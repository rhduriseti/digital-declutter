import hashlib
from pathlib import Path

# Files matching these patterns are temp/junk files — all copies are deletable,
# so every file in the group is marked as a duplicate with no "real" original.
TEMP_FILE_PREFIXES = {"~$"}


def is_temp_file(path: str) -> bool:
    name = Path(path).name
    return any(name.startswith(prefix) for prefix in TEMP_FILE_PREFIXES)


def compute_md5(path: str, chunk_size: int = 8192) -> str:
    """
    Compute MD5 hash of a file in a memory-efficient way.
    """
    hash_md5 = hashlib.md5()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def detect_duplicates(index: dict) -> dict:
    """
    Detect exact duplicates using MD5 hashing.

    MD5 computation is incremental — local files are only read from disk when
    they are new or their modified_at has changed since the MD5 was last computed.
    Drive files always use the MD5 stored in the index (fetched free from the API).

    Duplicate matching always runs in full across all stored MD5s — cheap since
    it is just dict lookups, and a newly added file could duplicate anything.

    Rules:
    - Files with identical MD5 hashes are duplicates
    - The first file encountered becomes the "original"
    - All others get duplicate_of = <original_path>
    """

    # Step 1: Resolve MD5 for each file — incremental for local files
    updated_index = {}

    for path, entry in index.items():
        stored_md5 = entry.get("md5")
        stored_md5_modified = entry.get("md5_computed_modified_at")
        current_modified = entry.get("modified_at")

        if stored_md5 and stored_md5_modified == current_modified:
            # MD5 is up to date — no disk read needed
            updated_index[path] = entry
            continue

        if stored_md5 and not stored_md5_modified:
            # Drive file (or old index entry with stored md5 but no timestamp) — trust it
            updated_index[path] = entry
            continue

        # Local file: new or modified — compute MD5 from disk
        file_path = Path(path)
        if not file_path.exists():
            updated_index[path] = entry
            continue

        md5 = compute_md5(path)
        updated_index[path] = {**entry, "md5": md5, "md5_computed_modified_at": current_modified}

    # Step 2: Clear duplicate_of and rebuild from stored MD5s
    for path in updated_index:
        updated_index[path]["duplicate_of"] = None

    md5_map: dict[str, list[str]] = {}
    for path, entry in updated_index.items():
        md5 = entry.get("md5")
        if md5:
            md5_map.setdefault(md5, []).append(path)

    # Step 3: Mark duplicates
    for md5, paths in md5_map.items():
        if len(paths) <= 1:
            continue

        if all(is_temp_file(p) for p in paths):
            for p in paths:
                updated_index[p]["duplicate_of"] = "__temp_file__"
            continue

        original = paths[0]
        for dup in paths[1:]:
            updated_index[dup]["duplicate_of"] = original

    return updated_index
