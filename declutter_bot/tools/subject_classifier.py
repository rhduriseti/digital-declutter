from fileinput import filename
import json
import re
from pathlib import Path
import ollama

from declutter_bot.core.utils import KEYWORD_TO_SUBJECT, SEED_MAP
from declutter_bot.core.paths import DATA_DIR, get_expanded_map_path

EXPANDED_MAP_PATH = get_expanded_map_path("local")

# Folder names too generic to use as subject signals
GENERIC_FOLDER_NAMES = {
    "documents", "downloads", "desktop", "files", "school",
    "homework", "assignments", "work", "misc", "stuff",
    "new folder", "untitled", "folder", "archive", "backup"
}

# Cached sentence-transformers model (loaded once on first Group C call)
_st_model = None


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
    Split text into lowercase keyword tokens.
    e.g. "AP_Bio_Chapter3_Notes" → ["ap", "bio", "chapter", "notes"]
    """
    text = text.lower()
    text = re.sub(r'\.\w+$', '', text)
    tokens = re.split(r'[^a-z]+', text)
    return [t for t in tokens if len(t) > 1]


# ---------------------------------------------------------
# Scoring engine (shared by Groups A and B)
# ---------------------------------------------------------

def score_text(text: str, expanded: dict | None = None) -> dict[str, int]:
    """
    Score text against SEED_MAP and optional expanded map.

    Rules:
    - Multi-word phrase match → 2 points (more specific signal)
    - Single-word keyword match → 1 point
    - Each unique keyword capped at 3 points (prevents repetition bias)
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for kw, subject in KEYWORD_TO_SUBJECT.items():
        weight = 2 if " " in kw else 1
        count = len(re.findall(r"\b" + re.escape(kw) + r"\b", text_lower))
        if count:
            scores[subject] = scores.get(subject, 0) + min(count * weight, 3)

    if expanded:
        for kw, subject in expanded.items():
            count = len(re.findall(r"\b" + re.escape(kw) + r"\b", text_lower))
            if count:
                scores[subject] = scores.get(subject, 0) + min(count, 3)

    return scores


def confidence_from_scores(scores: dict[str, int]) -> tuple[str | None, float]:
    """
    Compute (winner_subject, confidence) from scores dict.
    confidence = winner_score / total_score.
    Ties → capped at 0.3 so the next group gets a chance.
    """
    if not scores:
        return None, 0.0
    total = sum(scores.values())
    winner = max(scores, key=scores.get)
    winner_score = scores[winner]
    sorted_vals = sorted(scores.values(), reverse=True)
    if len(sorted_vals) > 1 and sorted_vals[0] == sorted_vals[1]:
        return winner, 0.3
    return winner, winner_score / total


# ---------------------------------------------------------
# File text reader (used by Groups B and C)
# ---------------------------------------------------------

def _read_file_text(file_path: str, max_chars: int) -> str:
    """Read first max_chars of a local file as text. Returns empty string on failure."""
    try:
        with open(file_path, "r", errors="ignore") as f:
            return f.read(max_chars)
    except (OSError, PermissionError, IsADirectoryError):
        return ""


def _metadata_text(file_path: str) -> str:
    """Build combined folder + filename text for Group A scoring."""
    path = Path(file_path)
    parts = [path.stem] + [
        p.name for p in path.parents
        if p.name and p.name.lower() not in GENERIC_FOLDER_NAMES
    ]
    return " ".join(parts)


# ---------------------------------------------------------
# Group A — metadata only (folder + filename keywords)
# ---------------------------------------------------------

def classify_group_a(file_path: str) -> tuple[str | None, float]:
    """Score folder names + filename against SEED_MAP and expanded map."""
    text = _metadata_text(file_path)
    expanded = load_expanded_map()
    scores = score_text(text, expanded)
    return confidence_from_scores(scores)


# ---------------------------------------------------------
# Group B — content keyword scoring (local text files)
# ---------------------------------------------------------

def classify_group_b(file_path: str, max_chars: int = 500) -> tuple[str | None, float]:
    """Read first max_chars of local file and score against SEED_MAP + expanded map."""
    content = _read_file_text(file_path, max_chars)
    if not content.strip():
        return None, 0.0
    expanded = load_expanded_map()
    scores = score_text(content, expanded)
    return confidence_from_scores(scores)


# ---------------------------------------------------------
# Group C — semantic similarity (sentence-transformers)
# Saves new keywords to the expanded map
# ---------------------------------------------------------

def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


def classify_group_c(text: str) -> tuple[str, float]:
    """
    Semantic similarity via sentence-transformers. Always returns a subject.
    New keywords found in the text are saved to the expanded map.
    Requires: pip install sentence-transformers
    """
    from sentence_transformers import util

    model = _get_st_model()
    subjects = list(SEED_MAP.keys())
    descriptions = [" ".join(SEED_MAP[s][:10]) for s in subjects]

    subject_embeddings = model.encode(descriptions, convert_to_tensor=True)
    text_embedding = model.encode(text[:2000], convert_to_tensor=True)

    similarities = util.cos_sim(text_embedding, subject_embeddings)[0]
    best_idx = int(similarities.argmax())
    best_score = float(similarities[best_idx])
    winner = subjects[best_idx]

    # Save tokens not already in SEED_MAP to expanded map (only when confident)
    if best_score > 0.5:
        for token in extract_keywords(text[:2000]):
            if token not in KEYWORD_TO_SUBJECT and len(token) > 3:
                save_to_expanded_map(token, winner)

    return winner, best_score


# ---------------------------------------------------------
# Legacy pipeline (steps 1-4) — kept for tests and backward compatibility
# ---------------------------------------------------------

def classify_by_folder(file_path: str) -> str | None:
    path = Path(file_path)
    for folder in path.parents:
        name = folder.name.lower()
        if name in GENERIC_FOLDER_NAMES:
            continue
        for kw in extract_keywords(name):
            if kw in KEYWORD_TO_SUBJECT:
                return KEYWORD_TO_SUBJECT[kw]
    return None


def classify_by_filename(file_path: str) -> str | None:
    name = Path(file_path).stem
    for kw in extract_keywords(name):
        if kw in KEYWORD_TO_SUBJECT:
            return KEYWORD_TO_SUBJECT[kw]
    return None


def classify_by_seed_map(file_path: str) -> str | None:
    path = Path(file_path)
    all_text = " ".join([path.stem] + [p.name for p in path.parents]).lower()
    scores: dict[str, int] = {}
    for kw, subject in KEYWORD_TO_SUBJECT.items():
        if " " in kw:
            if re.search(r"\b" + re.escape(kw) + r"\b", all_text):
                scores[subject] = scores.get(subject, 0) + 2
    for token in extract_keywords(all_text):
        if token in KEYWORD_TO_SUBJECT:
            subject = KEYWORD_TO_SUBJECT[token]
            scores[subject] = scores.get(subject, 0) + 1
    return max(scores, key=scores.get) if scores else None


def classify_by_expanded_map(file_path: str) -> str | None:
    expanded = load_expanded_map()
    if not expanded:
        return None
    path = Path(file_path)
    all_text = " ".join([path.stem] + [p.name for p in path.parents])
    for kw in extract_keywords(all_text):
        if kw in expanded:
            return expanded[kw]
    return None


def classify_subject(file_path: str) -> str | None:
    return (
        classify_by_folder(file_path) or
        classify_by_filename(file_path) or
        classify_by_seed_map(file_path) or
        classify_by_expanded_map(file_path)
    )


# ---------------------------------------------------------
# Ollama fallback
# ---------------------------------------------------------

def classify_by_ollama_ai(file_path: str) -> str | None:
    path = Path(file_path)

    prompt = f"""You are a school file organiser.
Given this filename: "{path.stem}"
From this folder: "{path.parent.name}"

Return a single JSON object with keys: "subject", "confidence", and optional "new_keywords".
Example:
{{"subject": "biology", "confidence": 0.92, "new_keywords": ["frankenstein"]}}

Choose only from: {", ".join(SEED_MAP.keys())}, other
"""

    response = ollama.chat(
        model="gemma3:4b",
        messages=[{"role": "user", "content": prompt}]
    )

    content = None
    if isinstance(response, dict):
        msg = response.get("message")
        if isinstance(msg, dict):
            content = msg.get("content")
        content = content or response.get("content")

    if not content:
        return None

    subject = None
    confidence = 0.0
    new_keywords: list[str] = []

    try:
        parsed = json.loads(content)
        subject = parsed.get("subject")
        confidence = float(parsed.get("confidence", 0))
        new_keywords = parsed.get("new_keywords", []) or []
    except Exception:
        m_sub = re.search(r"Subject:\s*(\w+)", content, re.I)
        m_conf = re.search(r"Confidence:\s*([0-9.]+)", content, re.I)
        subject = m_sub.group(1).lower() if m_sub else None
        confidence = float(m_conf.group(1)) if m_conf else 0.0
        m_new = re.search(r"New[_\s]*keywords:\s*(.+)", content, re.I)
        if m_new:
            items = re.split(r"[,;\\n]", m_new.group(1))
            new_keywords = [i.strip().lower() for i in items if i.strip()]

    if subject and new_keywords and confidence > 0.85:
        for kw in new_keywords:
            save_to_expanded_map(kw, subject)

    return subject
