from pathlib import Path
from declutter_bot.core.staging_manager import move_to_staging


def get_deletable_paths(index: dict, folder: str = None) -> list[dict]:
    """
    Return all files that are safe to delete (i.e. duplicates).
    Includes both regular duplicates and temp files (duplicate_of == '__temp_file__').
    If folder is given, only returns duplicates under that folder.
    """
    folder_path = Path(folder).resolve() if folder else None

    return [
        {
            "path": path,
            "duplicate_of": entry["duplicate_of"],
            "size_bytes": entry.get("size_bytes", 0),
        }
        for path, entry in index.items()
        if entry.get("duplicate_of")
        and (folder_path is None or Path(path).resolve().is_relative_to(folder_path))
    ]


def delete_duplicates(index: dict, targets: list[dict], permanent: bool = False) -> tuple:
    """
    Delete the given list of duplicate files from disk and remove them from the index.

    - permanent=False: moves files to staging folder (recoverable via 'staging restore')
    - permanent=True:  permanently deletes files (caller must confirm first)

    Returns (updated_index, deleted, skipped).
    """
    updated_index = {**index}
    deleted = []
    skipped = []

    for entry in targets:
        path = entry["path"]
        file_path = Path(path)

        if not file_path.exists():
            skipped.append(path)
            if path in updated_index:
                del updated_index[path]
            continue

        try:
            if permanent:
                file_path.unlink()
            else:
                move_to_staging(path)

            del updated_index[path]
            deleted.append(entry)

        except Exception as e:
            skipped.append(f"{path} (error: {e})")

    return updated_index, deleted, skipped
