import warnings

from declutter_bot.core.utils import CATEGORY_MAP
from declutter_bot.tools.subject_classifier import (
    classify_group_a,
    classify_group_b,
    classify_group_c,
    classify_by_ollama_ai,
    _read_file_text,
    score_text,
    confidence_from_scores,
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


def categorize_files(index: dict, on_progress=None) -> dict:
    """
    Categorise every file in the index using the 3-group pipeline.

    Group A — metadata only (folder + filename keywords). Fast, no file read.
    Group B — content keyword scan (500 then 2000 chars).
    Group C — sentence-transformers semantic similarity. Always returns a subject.
    Ollama  — primary AI classifier via local Gemma model.

    For Drive files, content is downloaded transiently into memory for Groups B/C.
    It is never written to disk or sent to any third party.

    Rules:
    - Skip entries where manually_set=True (student's choice is permanent)
    - Skip entries where category exists and file is unchanged since last categorisation
    - Store confidence_score and classification_group alongside category

    on_progress(done, total) — called after each file is processed.
    """
    updated_index = {}
    _st_available = True
    _ollama_available = True
    _drive_connectors: dict = {}

    total = len(index)
    done = 0

    for path, entry in index.items():
        # Never reclassify student corrections
        if entry.get("manually_set"):
            updated_index[path] = entry
            done += 1
            if on_progress:
                on_progress(done, total)
            continue

        current_modified = entry.get("modified_at")
        last_cat_modified = entry.get("categorised_modified_at")
        if entry.get("category") and last_cat_modified is not None and last_cat_modified == current_modified:
            updated_index[path] = entry
            done += 1
            if on_progress:
                on_progress(done, total)
            continue

        ext = entry.get("extension", "").lower()
        source = entry.get("source", "local")
        is_local = source == "local"
        is_drive = source.startswith("gdrive:")
        can_read_local = is_local and ext in CONTENT_READABLE_EXTENSIONS
        can_read_drive = is_drive and ext in CONTENT_READABLE_EXTENSIONS

        subject = None
        confidence = 0.0
        group = "fallback"

        # --- Group A: metadata scoring ---
        display_name = entry.get("name") if is_drive else None
        a_subject, a_confidence = classify_group_a(path, display_name)

        if a_confidence >= HIGH_CONFIDENCE:
            subject, confidence, group = a_subject, a_confidence, "A"

        elif can_read_local and a_confidence >= MED_CONFIDENCE:
            # --- Group B (local): keyword scan on 500 then 2000 chars ---
            b_subject, b_confidence = classify_group_b(path, 500)
            if b_confidence >= HIGH_CONFIDENCE:
                subject, confidence, group = b_subject, b_confidence, "B"
            elif b_confidence >= MED_CONFIDENCE:
                b2_subject, b2_confidence = classify_group_b(path, 2000)
                if b2_confidence >= MED_CONFIDENCE:
                    subject, confidence, group = b2_subject, b2_confidence, "B"

        # --- Group B (Drive): download content into memory, keyword scan ---
        if group == "fallback" and can_read_drive:
            drive_text = _get_drive_text(path, entry, source, _drive_connectors)
            if drive_text.strip():
                scores = score_text(drive_text)
                b_subject, b_confidence = confidence_from_scores(scores)
                if b_confidence >= MED_CONFIDENCE:
                    subject, confidence, group = b_subject, b_confidence, "B"

        # --- Group C: semantic similarity ---
        if group == "fallback" and _st_available:
            text = ""
            if can_read_local:
                text = _read_file_text(path, 2000)
            elif can_read_drive:
                text = _get_drive_text(path, entry, source, _drive_connectors)
            if text.strip():
                try:
                    c_subject, c_confidence = classify_group_c(text)
                    if c_subject is not None:
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

        # --- Ollama (local Gemma): AI classifier ---
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

        done += 1
        if on_progress:
            on_progress(done, total)

    return updated_index


def _get_drive_text(path: str, entry: dict, source: str, connectors: dict) -> str:
    """Download Drive file content into memory. Returns empty string on failure."""
    try:
        account_name = source.split(":", 1)[1]
        file_id = path.rsplit("/", 1)[-1]
        mime_type = entry.get("mime_type")
        ext = entry.get("extension", "")
        if account_name not in connectors:
            from declutter_bot.connectors.gdrive import GoogleDriveConnector
            connectors[account_name] = GoogleDriveConnector(account_name)
        return connectors[account_name].get_file_text(file_id, mime_type, max_chars=2000, ext=ext)
    except Exception:
        return ""
