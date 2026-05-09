import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

from declutter_bot.core.utils import CATEGORY_MAP
from declutter_bot.tools.subject_classifier import (
    classify_group_a,
    classify_group_b,
    classify_group_c,
    classify_group_c_visual,
    score_text,
    confidence_from_scores,
    _is_ambiguous,
    _read_file_text,
    VISUAL_EXTENSIONS,
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

# Groups A and B must clear this threshold AND be unambiguous to skip Gemma
HIGH_CONFIDENCE = 0.9
# Minimum total keyword score — prevents accidental matches from bypassing Gemma.
# Group A (filename) only needs 1: a subject word in the filename is strong evidence.
# Groups B+ need 4: content needs multiple hits to be trustworthy.
MIN_SCORE_A = 1
MIN_SCORE = 4


def categorize_files(index: dict, on_progress=None, max_workers: int = 4) -> dict:
    """
    Categorise every file in the index using the 3-group pipeline.

    Group A — metadata only (folder + filename keywords). Fast, no file read.
    Group B — content keyword scan against SEED_MAP.
    Group C — Gemma. Receives merged keyword scores as hints so it can reason
               about file PURPOSE rather than keyword presence alone.

    Rules:
    - Skip entries where manually_set=True (student's choice is permanent)
    - Skip entries where category exists and file is unchanged since last scan
    - Groups A and B only resolve a file when confidence >= 0.9 AND unambiguous
    - Group C is called for everything that doesn't hit that bar
    - Images try Gemma 4 Vision first, fall back to "media"
    - Audio/video always "media"
    - If all groups fail, category is "other"

    Files are processed concurrently (max_workers=4 by default) to reduce
    wall-clock time when many files hit Group C.
    on_progress(done, total) — called after each file is processed.
    """
    updated_index: dict = {}
    _lock = threading.Lock()
    _state = {"gemma_available": True, "done": 0}
    _drive_connectors: dict = {}
    total = len(index)

    def _process(path: str, entry: dict) -> tuple[str, dict]:
        # Never reclassify student corrections
        if entry.get("manually_set"):
            return path, entry

        current_modified = entry.get("modified_at")
        last_cat_modified = entry.get("categorised_modified_at")
        if (entry.get("category")
                and last_cat_modified is not None
                and last_cat_modified == current_modified):
            return path, entry

        ext = entry.get("extension", "").lower()
        source = entry.get("source", "local")
        is_local = source == "local"
        is_drive = source.startswith("gdrive:")
        can_read_local = is_local and ext in CONTENT_READABLE_EXTENSIONS
        can_read_drive = is_drive and ext in CONTENT_READABLE_EXTENSIONS
        is_media = ext in MEDIA_EXTENSIONS

        subject = None
        confidence = 0.0
        group = "fallback"
        c_also: str | None = None
        merged_scores: dict[str, int] = {}

        # --- Step 0: Media files ---
        # Images: try Gemma 4 Vision first; fall back to "media" if unavailable or personal.
        # Audio/video: extension is definitive.
        if is_media:
            with _lock:
                gemma_ok = _state["gemma_available"]
            if is_local and ext in VISUAL_EXTENSIONS and gemma_ok:
                _, _, a_scores = classify_group_a(path)
                try:
                    c_subject, c_confidence, c_also = classify_group_c_visual(path, a_scores)
                    if c_subject and c_subject != "other":
                        subject, confidence, group = c_subject, c_confidence, "C_visual"
                    else:
                        subject = CATEGORY_MAP.get(ext, "media")
                        group = "extension"
                except Exception:
                    with _lock:
                        _state["gemma_available"] = False
                    subject = CATEGORY_MAP.get(ext, "media")
                    group = "extension"
            else:
                subject = CATEGORY_MAP.get(ext, "media")
                group = "extension"

        else:
            # --- Group A: metadata scoring ---
            display_name = entry.get("name") if is_drive else None
            a_subject, a_confidence, a_scores = classify_group_a(path, display_name)

            for subj, pts in a_scores.items():
                merged_scores[subj] = merged_scores.get(subj, 0) + pts

            if (a_subject and a_confidence >= HIGH_CONFIDENCE
                    and not _is_ambiguous(merged_scores)
                    and sum(merged_scores.values()) >= MIN_SCORE_A):
                subject, confidence, group = a_subject, a_confidence, "A"

            # --- Group B: content keyword scan (local) ---
            if group == "fallback" and can_read_local:
                b_subject, b_confidence, b_scores = classify_group_b(path, 500)
                for subj, pts in b_scores.items():
                    merged_scores[subj] = merged_scores.get(subj, 0) + pts

                if (b_subject and b_confidence >= HIGH_CONFIDENCE
                        and not _is_ambiguous(merged_scores)
                        and sum(merged_scores.values()) >= MIN_SCORE):
                    subject, confidence, group = b_subject, b_confidence, "B"

                if group == "fallback":
                    b2_subject, b2_confidence, b2_scores = classify_group_b(path, 2000)
                    for subj, pts in b2_scores.items():
                        merged_scores[subj] = merged_scores.get(subj, 0) + pts
                    if (b2_subject and b2_confidence >= HIGH_CONFIDENCE
                            and not _is_ambiguous(merged_scores)
                            and sum(merged_scores.values()) >= MIN_SCORE):
                        subject, confidence, group = b2_subject, b2_confidence, "B"

            # --- Group B: content keyword scan (Drive) ---
            if group == "fallback" and can_read_drive:
                drive_text = _get_drive_text(path, entry, source, _drive_connectors, _lock)
                if drive_text.strip():
                    scores = score_text(drive_text)
                    for subj, pts in scores.items():
                        merged_scores[subj] = merged_scores.get(subj, 0) + pts
                    b_subject, b_confidence = confidence_from_scores(merged_scores)
                    if (b_subject and b_confidence >= HIGH_CONFIDENCE
                            and not _is_ambiguous(merged_scores)
                            and sum(merged_scores.values()) >= MIN_SCORE):
                        subject, confidence, group = b_subject, b_confidence, "B"

            # --- Group C: Gemma — contextual arbitrator ---
            with _lock:
                gemma_ok = _state["gemma_available"]
            if group == "fallback" and gemma_ok:
                text = ""
                if can_read_local:
                    text = _read_file_text(path, 2000)
                elif can_read_drive:
                    text = _get_drive_text(path, entry, source, _drive_connectors, _lock)
                try:
                    c_subject, c_confidence, c_also = classify_group_c(text, path, merged_scores)
                    if c_subject:
                        subject, confidence, group = c_subject, c_confidence, "C"
                except Exception:
                    with _lock:
                        _state["gemma_available"] = False
                    warnings.warn(
                        "Gemma is unavailable — classification skipped. "
                        "Set GOOGLE_API_KEY or start Ollama with 'ollama serve'.",
                        stacklevel=2,
                    )

        if subject is None:
            subject = "other"

        also_could_be = c_also if group in ("C", "C_visual") else None

        return path, {
            **entry,
            "category": subject,
            "confidence_score": round(confidence, 3),
            "classification_group": group,
            "also_could_be": also_could_be,
            "categorised_modified_at": current_modified,
        }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process, path, entry): path
            for path, entry in index.items()
        }
        for future in as_completed(futures):
            path, result = future.result()
            with _lock:
                updated_index[path] = result
                _state["done"] += 1
                if on_progress:
                    on_progress(_state["done"], total)

    return updated_index


def _get_drive_text(
    path: str, entry: dict, source: str, connectors: dict, lock: threading.Lock
) -> str:
    """Download Drive file content into memory. Returns empty string on failure."""
    try:
        account_name = source.split(":", 1)[1]
        file_id = path.rsplit("/", 1)[-1]
        mime_type = entry.get("mime_type")
        ext = entry.get("extension", "")
        with lock:
            if account_name not in connectors:
                from declutter_bot.connectors.gdrive import GoogleDriveConnector
                connectors[account_name] = GoogleDriveConnector(account_name)
            connector = connectors[account_name]
        return connector.get_file_text(file_id, mime_type, max_chars=2000, ext=ext)
    except Exception:
        return ""
