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

    Recomputes from scratch on every call to avoid stale or cyclic data
    from previous runs.

    Rules:
    - Files with identical MD5 hashes are duplicates
    - The first file encountered becomes the "original"
    - All others get duplicate_of = <original_path>
    """

    # Step 1: Clear all existing duplicate_of values
    updated_index = {
        path: {**entry, "duplicate_of": None}
        for path, entry in index.items()
    }

    # Step 2: Compute MD5 for each file
    md5_map = {}  # md5 → list of file paths

    for path in updated_index:
        file_path = Path(path)

        if not file_path.exists():
            continue

        md5 = compute_md5(path)
        md5_map.setdefault(md5, []).append(path)

    # Step 3: Mark duplicates
    for md5, paths in md5_map.items():
        if len(paths) <= 1:
            continue

        # If all files in the group are temp files, mark every one as deletable
        if all(is_temp_file(p) for p in paths):
            for p in paths:
                updated_index[p]["duplicate_of"] = "__temp_file__"
            continue

        original = paths[0]

        for dup in paths[1:]:
            updated_index[dup]["duplicate_of"] = original

    return updated_index
