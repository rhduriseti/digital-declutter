from declutter_bot.core.utils import CATEGORY_MAP
from declutter_bot.tools.subject_classifier import classify_subject


def categorize_files(index: dict) -> dict:
    """
    Add a 'category' field to each file entry in the index.

    Rules:
    1. If a file already has a category (e.g., user override), preserve it
    2. Run subject classifier (steps 1-4) — returns subject if found
    3. Fall back to extension-based CATEGORY_MAP
    4. If nothing matches → "other"
    """

    updated_index = {}

    for path, entry in index.items():
        # Preserve existing category if present
        if entry.get("category"):
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

        updated_index[path] = {**entry, "category": category}

    return updated_index
