from collections import Counter
from pathlib import Path

def generate_report_for_scan(index: dict, folder: Path) -> dict:
    folder_str = str(folder)

    # Filter index to only files under this folder
    subset = {
        path: entry
        for path, entry in index.items()
        if Path(path).resolve().is_relative_to(folder.resolve())
}

    if not subset:
        return {
            "total_files": 0,
            "total_size_bytes": 0,
            "categories": {},
            "duplicates": [],
            "space_saved_by_deleting_duplicates_bytes": 0,
        }

    total_files = len(subset)
    total_size = sum(e.get("size_bytes", 0) for e in subset.values())

    categories = Counter(
        e.get("category", "other") for e in subset.values()
    )

    # Individual duplicate files within this folder subset
    duplicate_files = [
        {
            "path": path,
            "duplicate_of": entry["duplicate_of"],
            "size_bytes": entry.get("size_bytes", 0),
            "category": entry.get("category"),
        }
        for path, entry in subset.items()
        if entry.get("duplicate_of")
    ]

    space_saved_by_deleting_duplicates = sum(f["size_bytes"] for f in duplicate_files)

    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "categories": dict(categories),
        "duplicates": duplicate_files,
        "space_saved_by_deleting_duplicates_bytes": space_saved_by_deleting_duplicates,
    }


def generate_report(index: dict) -> dict:
    """
    Generate a summary report from the index.

    Report includes:
    - total file count
    - total size
    - category breakdown
    - duplicate groups
    - largest files
    """

    if not index:
        return {
            "total_files": 0,
            "total_size_bytes": 0,
            "categories": {},
            "duplicates": [],
            "space_saved_by_deleting_duplicates_bytes": 0,
            "largest_files": [],
        }

    # ---------------------------------------------------------
    # Total files + total size
    # ---------------------------------------------------------
    total_files = len(index)
    total_size = sum(entry.get("size_bytes", 0) for entry in index.values())

    # ---------------------------------------------------------
    # Category breakdown
    # ---------------------------------------------------------
    categories = Counter(
        entry.get("category", "other") for entry in index.values()
    )

    # ---------------------------------------------------------
    # Individual duplicate files
    # ---------------------------------------------------------
    duplicate_files = [
        {
            "path": path,
            "duplicate_of": entry["duplicate_of"],
            "size_bytes": entry.get("size_bytes", 0),
            "category": entry.get("category"),
        }
        for path, entry in index.items()
        if entry.get("duplicate_of")
    ]

    space_saved = sum(f["size_bytes"] for f in duplicate_files)

    # ---------------------------------------------------------
    # Largest files (top 10)
    # ---------------------------------------------------------
    largest_files = sorted(
        index.values(),
        key=lambda e: e.get("size_bytes", 0),
        reverse=True
    )[:10]

    # ---------------------------------------------------------
    # Final report
    # ---------------------------------------------------------
    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "categories": dict(categories),
        "duplicates": duplicate_files,
        "space_saved_by_deleting_duplicates_bytes": space_saved,
        "largest_files": [
            {
                "path": f["path"],
                "size_bytes": f["size_bytes"],
                "category": f.get("category"),
            }
            for f in largest_files
        ],
    }
