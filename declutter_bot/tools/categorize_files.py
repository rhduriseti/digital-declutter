from declutter_bot.core.utils import CATEGORY_MAP
from declutter_bot.tools.subject_classifier import classify_subject, classify_by_ollama_ai

# Extensions where Ollama adds no value — filename alone isn't enough to classify
# and multimodal support (LLaVA, Gemini) is planned for Tier 2
OLLAMA_SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp",  # images
    ".mp4", ".mov", ".avi", ".mkv", ".wmv",                     # video
    ".mp3", ".wav", ".aac", ".flac",                            # audio
}


def categorize_files(index: dict) -> dict:
    """
    Add a 'category' field to each file entry in the index.

    Rules:
    1. Skip if already categorised AND modified_at hasn't changed (filename/folder unchanged)
    2. Run subject classifier (steps 1-4) — returns subject if found
    3. Step 5: Ollama AI — only for text-based file types (skip media files)
    4. Fall back to extension-based CATEGORY_MAP
    5. If nothing matches → "other"

    Stores 'categorised_modified_at' alongside 'category' so future runs can detect
    whether the file changed since it was last categorised.
    """

    updated_index = {}
    _ollama_available = True

    for path, entry in index.items():
        current_modified = entry.get("modified_at")

        # Skip if already categorised and file hasn't changed since last categorisation.
        # If categorised_modified_at is absent (old index entry), treat as unchanged.
        last_cat_modified = entry.get("categorised_modified_at", current_modified)
        if entry.get("category") and last_cat_modified == current_modified:
            updated_index[path] = entry
            continue

        # Step 1-4: try subject classification first
        subject = classify_subject(path)

        if subject:
            category = subject
        else:
            ext = entry.get("extension", "").lower()
            # Step 5: Ollama AI — skip media files, they need multimodal (Tier 2)
            if ext not in OLLAMA_SKIP_EXTENSIONS and _ollama_available:
                try:
                    subject = classify_by_ollama_ai(path)
                except Exception:
                    _ollama_available = False
                    import warnings
                    warnings.warn(
                        "Ollama server is unavailable — AI classification skipped. "
                        "Start Ollama with 'ollama serve' to enable it.",
                        stacklevel=2,
                    )
            category = subject or CATEGORY_MAP.get(ext, "other")

        updated_index[path] = {**entry, "category": category, "categorised_modified_at": current_modified}

    return updated_index
