import warnings

from declutter_bot.core.utils import CATEGORY_MAP
from declutter_bot.tools.subject_classifier import (
    classify_group_a,
    classify_group_b,
    classify_group_c,
    classify_by_ollama_ai,
    _read_file_text,
)

# Extensions where content reading adds value
CONTENT_READABLE_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".doc", ".docx", ".rtf",
    ".ppt", ".pptx", ".html", ".htm", ".csv",
}

# Extensions where content reading has no value (media)
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp",
    ".mp4", ".mov", ".avi", ".mkv", ".wmv",
    ".mp3", ".wav", ".aac", ".flac",
}

# Thresholds
HIGH_CONFIDENCE = 0.7
MED_CONFIDENCE = 0.4


def categorize_files(index: dict) -> dict:
    """
    Categorise every file in the index using the 3-group pipeline.

    Group A — metadata only (folder + filename keywords). Fast, no file read.
    Group B — content keyword scan (500 then 2000 chars). Local text files only.
    Group C — sentence-transformers semantic similarity. Always returns a subject.
    Ollama  — fallback if sentence-transformers not installed.

    Rules:
    - Skip entries where manually_set=True (student's choice is permanent)
    - Skip entries where category exists and file is unchanged since last categorisation
    - Store confidence_score and classification_group alongside category
    """
    updated_index = {}
    _st_available = True
    _ollama_available = True

    for path, entry in index.items():
        # Never reclassify student corrections
        if entry.get("manually_set"):
            updated_index[path] = entry
            continue

        current_modified = entry.get("modified_at")
        last_cat_modified = entry.get("categorised_modified_at", current_modified)
        if entry.get("category") and last_cat_modified == current_modified:
            updated_index[path] = entry
            continue

        ext = entry.get("extension", "").lower()
        source = entry.get("source", "local")
        is_local = source == "local"
        can_read = is_local and ext in CONTENT_READABLE_EXTENSIONS

        subject = None
        confidence = 0.0
        group = "fallback"

        # --- Group A: metadata scoring ---
        a_subject, a_confidence = classify_group_a(path)

        if a_confidence >= HIGH_CONFIDENCE:
            subject, confidence, group = a_subject, a_confidence, "A"

        elif a_confidence >= MED_CONFIDENCE and can_read:
            # --- Group B: content 500 chars ---
            b_subject, b_confidence = classify_group_b(path, 500)
            if b_confidence >= HIGH_CONFIDENCE:
                subject, confidence, group = b_subject, b_confidence, "B"
            elif b_confidence >= MED_CONFIDENCE:
                # Try 2000 chars
                b2_subject, b2_confidence = classify_group_b(path, 2000)
                if b2_confidence >= MED_CONFIDENCE:
                    subject, confidence, group = b2_subject, b2_confidence, "B"

        # --- Group C: semantic similarity ---
        if group == "fallback" and can_read and _st_available:
            try:
                text = _read_file_text(path, 2000)
                if text.strip():
                    c_subject, c_confidence = classify_group_c(text)
                    subject, confidence, group = c_subject, c_confidence, "C"
            except ImportError:
                _st_available = False
                warnings.warn(
                    "sentence-transformers not installed — Group C skipped. "
                    "Install with: pip install sentence-transformers",
                    stacklevel=2,
                )
            except Exception:
                _st_available = False

        # --- Ollama fallback (when sentence-transformers unavailable) ---
        if group == "fallback" and ext not in MEDIA_EXTENSIONS and _ollama_available:
            try:
                ol_subject = classify_by_ollama_ai(path)
                if ol_subject:
                    subject, group = ol_subject, "ollama"
            except Exception:
                _ollama_available = False
                warnings.warn(
                    "Ollama server is unavailable — AI classification skipped. "
                    "Start Ollama with 'ollama serve' to enable it.",
                    stacklevel=2,
                )

        # --- Final fallback: extension map ---
        if subject is None:
            subject = CATEGORY_MAP.get(ext, "other")

        updated_index[path] = {
            **entry,
            "category": subject,
            "confidence_score": round(confidence, 3),
            "classification_group": group,
            "categorised_modified_at": current_modified,
        }

    return updated_index
