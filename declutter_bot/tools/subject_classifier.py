from fileinput import filename
import json
import re
from pathlib import Path
import ollama

from declutter_bot.core.utils import KEYWORD_TO_SUBJECT, SEED_MAP
from declutter_bot.core.paths import DATA_DIR, EXPANDED_MAP_PATH

# Folder names that are too generic to use as subject signals
GENERIC_FOLDER_NAMES = {
    "documents", "downloads", "desktop", "files", "school",
    "homework", "assignments", "work", "misc", "stuff",
    "new folder", "untitled", "folder", "archive", "backup"
}


# ---------------------------------------------------------
# Expanded map helpers
# ---------------------------------------------------------

def load_expanded_map() -> dict[str, str]:
    """Load the auto-learned keyword → subject map."""
    if not EXPANDED_MAP_PATH.exists():
        return {}
    with open(EXPANDED_MAP_PATH, "r") as f:
        return json.load(f)


def save_to_expanded_map(keyword: str, subject: str):
    """Save a newly learned keyword → subject mapping."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    expanded = load_expanded_map()
    expanded[keyword.lower()] = subject
    with open(EXPANDED_MAP_PATH, "w") as f:
        json.dump(expanded, f, indent=2)


# ---------------------------------------------------------
# Keyword extraction helper
# ---------------------------------------------------------

def extract_keywords(text: str) -> list[str]:
    """
    Split a filename or folder name into lowercase keywords.
    Handles separators: spaces, underscores, hyphens, dots, digits.

    e.g. "AP_Bio_Chapter3_Notes" → ["ap", "bio", "chapter", "notes"]
    """
    text = text.lower()
    # Remove file extension if present
    text = re.sub(r'\.\w+$', '', text)
    # Split on non-alpha characters
    tokens = re.split(r'[^a-z]+', text)
    return [t for t in tokens if len(t) > 1]


# ---------------------------------------------------------
# Step 1 — Folder context
# ---------------------------------------------------------

def classify_by_folder(file_path: str) -> str | None:
    """
    Step 1: Check folder names in the path for subject keywords.
    Works from the immediate parent upward, stops at first match.

    e.g. ~/Documents/AP Bio/notes.pdf → "biology"
    """
    path = Path(file_path)

    for folder in path.parents:
        name = folder.name.lower()
        if name in GENERIC_FOLDER_NAMES:
            continue
        keywords = extract_keywords(name)
        for kw in keywords:
            if kw in KEYWORD_TO_SUBJECT:
                return KEYWORD_TO_SUBJECT[kw]

    return None


# ---------------------------------------------------------
# Step 2 — Filename keywords
# ---------------------------------------------------------

def classify_by_filename(file_path: str) -> str | None:
    """
    Step 2: Check the filename itself for subject keywords.

    e.g. "calc_test_2.pdf" → "math"
    """
    name = Path(file_path).stem
    keywords = extract_keywords(name)

    for kw in keywords:
        if kw in KEYWORD_TO_SUBJECT:
            return KEYWORD_TO_SUBJECT[kw]

    return None


# ---------------------------------------------------------
# Step 3 — Seed map (already covered by KEYWORD_TO_SUBJECT)
# Kept as explicit step for clarity — same lookup, different source
# ---------------------------------------------------------

def classify_by_seed_map(file_path: str) -> str | None:
    """
    Step 3: Full keyword scan against the seed map.
    Checks both folder and filename tokens together.
    Catches cases where step 1 & 2 missed due to generic folder names.
    """
    path = Path(file_path)
    all_text = " ".join([path.stem] + [p.name for p in path.parents])
    keywords = extract_keywords(all_text)

    for kw in keywords:
        if kw in KEYWORD_TO_SUBJECT:
            return KEYWORD_TO_SUBJECT[kw]

    return None


# ---------------------------------------------------------
# Step 4 — Expanded map (auto-learned from AI)
# ---------------------------------------------------------

def classify_by_expanded_map(file_path: str) -> str | None:
    """
    Step 4: Check the auto-learned expanded keyword map.
    This grows over time as the AI (step 5) identifies new keywords.

    e.g. "frankenstein" → "english"  (learned from a previous AI call)
    """
    expanded = load_expanded_map()
    if not expanded:
        return None

    path = Path(file_path)
    all_text = " ".join([path.stem] + [p.name for p in path.parents])
    keywords = extract_keywords(all_text)

    for kw in keywords:
        if kw in expanded:
            return expanded[kw]

    return None


# ---------------------------------------------------------
# Main classifier — runs steps 1-4 in order
# ---------------------------------------------------------

def classify_subject(file_path: str) -> str | None:
    """
    Run steps 1-4 of the subject classification pipeline.
    Returns the subject string or None if no match found.

    Steps:
    1. Folder name context
    2. Filename keywords
    3. Seed map (full path scan)
    4. Expanded map (AI-learned keywords)

    Step 5 (Ollama AI) is handled separately in subject_classifier_ai.py
    """
    return (
        classify_by_folder(file_path) or
        classify_by_filename(file_path) or
        classify_by_seed_map(file_path) or
        classify_by_expanded_map(file_path)
    )

def classify_by_ollama_ai(file_path: str) -> str | None:
    """
    Step 5: Use Ollama AI for classification when all keyword-based methods fail.
    This is a costly operation, so it's only called as a last resort.

    The AI can also return new keyword → subject mappings, which we save to the expanded map.
    """
    # Ensure we work with a Path
    path = Path(file_path)

    # Ask the model to return a JSON object for easier parsing
    prompt = f"""You are a school file organiser.
Given this filename: "{path.stem}"
From this folder: "{path.parent.name}"

Return a single JSON object with keys: "subject", "confidence", and optional "new_keywords".
Example:
{{"subject": "biology", "confidence": 0.92, "new_keywords": ["frankenstein"]}}

Choose only from: {", ".join(SEED_MAP.keys())}, other
"""

    # Send prompt to Ollama and extract text content robustly
    response = ollama.chat(
        model="gemma3:4b",
        messages=[{"role": "user", "content": prompt}]
    )

    # Ollama's python client places the text in response["message"]["content"]
    content = None
    if isinstance(response, dict):
        msg = response.get("message")
        if isinstance(msg, dict):
            content = msg.get("content")
        content = content or response.get("content")

    if not content:
        return None

    # Try JSON parse first, fall back to regex extraction
    subject = None
    confidence = 0.0
    new_keywords: list[str] = []

    try:
        parsed = json.loads(content)
        subject = parsed.get("subject")
        confidence = float(parsed.get("confidence", 0))
        new_keywords = parsed.get("new_keywords", []) or []
    except Exception:
        # Fallback: parse lines like 'Subject: <name>' and 'Confidence: <num>'
        m_sub = re.search(r"Subject:\s*(\w+)", content, re.I)
        m_conf = re.search(r"Confidence:\s*([0-9.]+)", content, re.I)
        subject = m_sub.group(1).lower() if m_sub else None
        confidence = float(m_conf.group(1)) if m_conf else 0.0
        m_new = re.search(r"New[_\s]*keywords:\s*(.+)", content, re.I)
        if m_new:
            items = re.split(r"[,;\\n]", m_new.group(1))
            new_keywords = [i.strip().lower() for i in items if i.strip()]

    # Save new keywords to expanded map only when confident
    if subject and new_keywords and confidence > 0.85:
        for kw in new_keywords:
            save_to_expanded_map(kw, subject)

    return subject
