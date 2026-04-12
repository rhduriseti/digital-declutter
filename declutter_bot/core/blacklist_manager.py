import json
from pathlib import Path

from declutter_bot.core.paths import DATA_DIR, BLACKLIST_PATH


def load_blacklist() -> set[str]:
    """Return the set of blacklisted folder paths."""
    if not BLACKLIST_PATH.exists():
        return set()
    with open(BLACKLIST_PATH, "r") as f:
        data = json.load(f)
    return set(data.get("folders", []))


def save_blacklist(folders: set[str]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(BLACKLIST_PATH, "w") as f:
        json.dump({"folders": sorted(folders)}, f, indent=2)


def add_to_blacklist(folder: str) -> tuple[bool, int]:
    """
    Add a folder to the blacklist and purge its entries from the index.
    Returns (was_newly_added, number_of_index_entries_removed).
    """
    from declutter_bot.core.index_manager import load_index, save_index

    resolved = Path(folder).resolve()
    path_str = str(resolved)
    folders = load_blacklist()

    if path_str in folders:
        return False, 0

    folders.add(path_str)
    save_blacklist(folders)

    # Purge all index entries under this folder
    index = load_index()
    purged = {
        p: e for p, e in index.items()
        if not Path(p).resolve().is_relative_to(resolved)
    }
    removed = len(index) - len(purged)
    if removed > 0:
        save_index(purged)

    return True, removed


def remove_from_blacklist(folder: str) -> bool:
    """Remove a folder from the blacklist. Returns True if it was found and removed."""
    path = str(Path(folder).resolve())
    folders = load_blacklist()
    if path not in folders:
        return False
    folders.discard(path)
    save_blacklist(folders)
    return True


def is_blacklisted(folder: str) -> bool:
    """Return True if this folder or any of its parents is blacklisted."""
    path = Path(folder).resolve()
    blacklist = {Path(bl) for bl in load_blacklist()}
    return any(
        path == bl or bl in path.parents
        for bl in blacklist
    )
