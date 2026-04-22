import json
from pathlib import Path
from typing import List, Dict

from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.paths import get_index_path, DRIVE_ACCOUNTS_DIR


def load_index(source_id: str = "local") -> Dict[str, dict]:
    """Load index for a specific source. Returns empty dict if not found."""
    path = get_index_path(source_id)
    if not path.exists():
        return {}
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("files", {})


def save_index(index: Dict[str, dict], source_id: str = "local"):
    """Save index for a specific source."""
    path = get_index_path(source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"files": index}, f, indent=2, default=str)


def load_combined_index() -> Dict[str, dict]:
    """
    Merge all available indexes into one dict for reporting and search.
    Only loads indexes for connected accounts (those with a token file).
    Disconnected accounts are automatically excluded — no cleanup needed.
    Reconnecting an account instantly restores its index without rescanning.
    """
    combined = {}
    combined.update(load_index("local"))

    if DRIVE_ACCOUNTS_DIR.exists():
        for token_file in DRIVE_ACCOUNTS_DIR.glob("*.json"):
            account_name = token_file.stem
            source_id = f"gdrive:{account_name}"
            combined.update(load_index(source_id))

    return combined


def untrack_folder(folder: str) -> int:
    """
    Remove all local index entries whose path is under the given folder.
    Does not blacklist — the folder can be added back and scanned again later.
    Returns number of entries removed.
    """
    folder_path = Path(folder).resolve()
    index = load_index("local")
    kept = {
        p: e for p, e in index.items()
        if not Path(p).resolve().is_relative_to(folder_path)
    }
    removed = len(index) - len(kept)
    if removed > 0:
        save_index(kept, "local")
    return removed


def purge_source_from_index(source_id: str) -> int:
    """
    Only used for blacklist-style purges where data should be permanently removed.
    Logout does NOT call this — token deletion is enough to hide the data.
    Returns number of entries removed.
    """
    path = get_index_path(source_id)
    if not path.exists():
        return 0
    index = load_index(source_id)
    removed = len(index)
    path.unlink()
    return removed


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
    new_scan_dict = {str(item.path): item for item in new_scan}

    for path, old_entry in existing_index.items():
        if path not in new_scan_dict:
            updated_index[path] = old_entry
            continue

        new_item = new_scan_dict[path]

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


def update_index_with_scan(new_scan: List[FileMetadata], source_id: str = "local"):
    """
    Load index for this source, merge new scan results, save back.
    """
    existing = load_index(source_id)
    merged = merge_scans(existing, new_scan)
    save_index(merged, source_id)
