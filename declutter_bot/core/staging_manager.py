import json
import shutil
from datetime import datetime
from pathlib import Path

from declutter_bot.core.index_manager import load_index, save_index
from declutter_bot.core.paths import DATA_DIR, STAGING_LOG_PATH

STAGING_DIR = Path.home() / ".declutter_staging"


def load_staging_log() -> dict:
    if not STAGING_LOG_PATH.exists():
        return {}
    with open(STAGING_LOG_PATH, "r") as f:
        return json.load(f)


def save_staging_log(log: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STAGING_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2, default=str)


def move_to_staging(file_path: str) -> str:
    """
    Move a file to the staging folder.
    Returns the staged path.
    Raises FileNotFoundError if the file doesn't exist.
    """
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    src = Path(file_path)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Avoid name collisions in staging by appending a short unique suffix
    import uuid
    suffix = uuid.uuid4().hex[:6]
    staged_name = f"{src.stem}_{suffix}{src.suffix}"
    dst = STAGING_DIR / staged_name

    shutil.move(str(src), str(dst))

    # Grab the index entry before it gets removed so we can restore it later
    index = load_index()
    index_entry = index.get(file_path)

    # Record in log
    log = load_staging_log()
    log[file_path] = {
        "original_path": file_path,
        "staged_path": str(dst),
        "staged_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "size_bytes": dst.stat().st_size,
        "index_entry": index_entry,
    }
    save_staging_log(log)

    return str(dst)


def restore_file(original_path: str) -> bool:
    """
    Restore a file from staging back to its original location.
    Returns True if restored, False if not found in log.
    """
    log = load_staging_log()

    if original_path not in log:
        return False

    entry = log[original_path]
    staged = Path(entry["staged_path"])
    dst = Path(original_path)

    if not staged.exists():
        # Already gone from staging — clean up log entry
        del log[original_path]
        save_staging_log(log)
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staged), str(dst))

    # Restore the index entry — clear duplicate_of since user is keeping this file
    index_entry = entry.get("index_entry")
    if index_entry:
        index_entry["duplicate_of"] = None
        index = load_index()
        index[original_path] = index_entry
        save_index(index)

    del log[original_path]
    save_staging_log(log)
    return True


def restore_all() -> tuple[int, int]:
    """
    Restore all staged files.
    Returns (restored_count, failed_count).
    """
    log = load_staging_log()
    restored = 0
    failed = 0

    for original_path in list(log.keys()):
        if restore_file(original_path):
            restored += 1
        else:
            failed += 1

    return restored, failed


def empty_staging() -> tuple[int, int]:
    """
    Permanently delete all files in staging and clear the log.
    Returns (deleted_count, total_bytes_freed).
    """
    log = load_staging_log()
    deleted = 0
    bytes_freed = 0

    for entry in log.values():
        staged = Path(entry["staged_path"])
        if staged.exists():
            bytes_freed += staged.stat().st_size
            staged.unlink()
            deleted += 1

    save_staging_log({})
    return deleted, bytes_freed


def get_staging_summary() -> list[dict]:
    """Return all staged files with their details."""
    log = load_staging_log()
    return list(log.values())
