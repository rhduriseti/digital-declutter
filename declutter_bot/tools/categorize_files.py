from declutter_bot.core.utils import CATEGORY_MAP
from declutter_bot.tools.subject_classifier import classify_subject


def categorize_files(index: dict) -> dict:
    """
    Add a 'category' field to each file entry in the index.

    Rules:
    1. Skip if already categorised AND modified_at hasn't changed (filename/folder unchanged)
    2. Run subject classifier (steps 1-4) — returns subject if found
    3. Fall back to extension-based CATEGORY_MAP
    4. If nothing matches → "other"

    Stores 'categorised_modified_at' alongside 'category' so future runs can detect
    whether the file changed since it was last categorised.
    """

    updated_index = {}

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
            # Fall back to extension-based category
            ext = entry.get("extension", "").lower()
            category = CATEGORY_MAP.get(ext, "other")

        updated_index[path] = {**entry, "category": category, "categorised_modified_at": current_modified}

    return updated_index
