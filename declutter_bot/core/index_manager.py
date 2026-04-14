import json
from typing import List, Dict

from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.paths import INDEX_PATH

def load_index() -> Dict[str, dict]:
    """
    Load index.json and return a dictionary keyed by file path.
    If the file doesn't exist, return an empty index.
    """
    if not INDEX_PATH.exists():
        return {}

    with open(INDEX_PATH, "r") as f:
        data = json.load(f)

    return data.get("files", {})



def save_index(index: Dict[str, dict]):
    """
    Save the index dictionary back to index.json.
    """
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "files": index
    }

    with open(INDEX_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def merge_scans(existing_index: Dict[str, dict],
                new_scan: List[FileMetadata]) -> Dict[str, dict]:
    """
    Merge new scan results into the existing index.

    Rules:
    - If file is new → add it
    - If file exists but timestamps changed → update metadata
    - If file exists and unchanged → keep existing (preserve category, duplicate info)
    - DO NOT delete files just because they weren't in this scan
    """

    updated_index = {}

    # Convert new scan to a dict keyed by path
    new_scan_dict = {str(item.path): item for item in new_scan}

    # 1. Handle existing files
    for path, old_entry in existing_index.items():

        if path not in new_scan_dict:
            # File wasn't in this scan → keep it
            updated_index[path] = old_entry
            continue

        new_item = new_scan_dict[path]

        # Check if timestamps changed
        if old_entry["modified_at"] != str(new_item.modified_at):
            updated_entry = {
                "path": str(new_item.path),
                "name": new_item.name,
                "extension": new_item.extension,
                "size_bytes": new_item.size_bytes,
                "created_at": str(new_item.created_at),
                "modified_at": str(new_item.modified_at),
                "source": new_item.source,
                "md5": new_item.md5,
                "web_view_link": new_item.web_view_link,
                "category": old_entry.get("category"),
                "duplicate_of": old_entry.get("duplicate_of"),
            }
        else:
            updated_entry = old_entry

        updated_index[path] = updated_entry

    # 2. Handle new files
    for path, item in new_scan_dict.items():
        if path not in updated_index:
            updated_index[path] = {
                "path": str(item.path),
                "name": item.name,
                "extension": item.extension,
                "size_bytes": item.size_bytes,
                "created_at": str(item.created_at),
                "modified_at": str(item.modified_at),
                "source": item.source,
                "md5": item.md5,
                "web_view_link": item.web_view_link,
                "category": None,
                "duplicate_of": None,
            }

    return updated_index



def update_index_with_scan(new_scan: List[FileMetadata]):
    """
    High-level function:
    - load index
    - merge
    - save
    """
    existing = load_index()
    merged = merge_scans(existing, new_scan)
    save_index(merged)
