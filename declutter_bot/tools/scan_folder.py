import os
from pathlib import Path
from typing import List

from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.blacklist_manager import is_blacklisted

'''
def scan_folder(folder_path: str) -> List[FileMetadata]:
    """
    Walk through a folder recursively and return a list of FileMetadata objects.
    """
    root = Path(folder_path).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {root}")

    metadata_list: List[FileMetadata] = []

    for path in root.rglob("*"):
        if path.is_file():
            try:
                metadata = FileMetadata.from_path(path)
                metadata_list.append(metadata)
            except Exception as e:
                # Skip unreadable or restricted files
                print(f"Skipping {path}: {e}")

    return metadata_list
'''

from pathlib import Path
from typing import List, Set

# ---------------------------------------------------------
# HARD-BLOCKED FOLDERS (NEVER SCAN)
# ---------------------------------------------------------

HARD_BLOCKED_FOLDERS: Set[str] = {
    # macOS
    "System", "Library", "Applications", "private", "opt",
    "usr", "bin", "sbin", "var",

    # Windows
    "Windows", "Program Files", "Program Files (x86)",
    "ProgramData", "AppData",

    # Cross-platform
    "__pycache__", "node_modules", "venv", ".venv", ".git",
    ".cache", ".config", ".vscode", "tmp", "temp"
}

# ---------------------------------------------------------
# FILE EXTENSION WHITELIST
# ---------------------------------------------------------

DOC_WHITELIST = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx", ".txt", ".md"
}

IMAGE_WHITELIST = {
    ".jpg", ".jpeg", ".png", ".heic"
}

VIDEO_WHITELIST = {
    ".mp4", ".mov"
}

PROGRAMMING_WHITELIST = {
    ".py", ".ipynb", ".java", ".cpp", ".c",
    ".js", ".html", ".css"
}

EXT_WHITELIST = (
    DOC_WHITELIST |
    IMAGE_WHITELIST |
    VIDEO_WHITELIST |
    PROGRAMMING_WHITELIST
)

# ---------------------------------------------------------
# FILE EXTENSION BLACKLIST
# ---------------------------------------------------------

EXT_BLACKLIST = {
    ".zip", ".exe", ".dmg", ".pkg", ".iso", ".app",
    ".msi", ".torrent", ".log", ".json", ".xml",
    ".pyc", ".db", ".sqlite", ".mp3", ".wav"
}

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def is_hidden(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    # Windows hidden attribute (AttributeError on macOS/Linux — safe to ignore)
    try:
        import os, stat
        return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
    except (AttributeError, OSError):
        return False

def is_symlink(path: Path) -> bool:
    return path.is_symlink()

# Files/folders whose presence marks a directory as a project (not user content)
PROJECT_MARKERS = {
    ".git", "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "Cargo.toml", "Makefile", "CMakeLists.txt",
    "pom.xml", "build.gradle", ".xcode", "*.xcodeproj",
}

def is_project_folder(folder: Path) -> bool:
    """Return True if the folder looks like a dev/project folder."""
    for marker in PROJECT_MARKERS:
        if "*" in marker:
            if any(folder.glob(marker)):
                return True
        elif (folder / marker).exists():
            return True
    return False

def is_hard_blocked(path: Path) -> bool:
    parts = {p.name for p in path.parents}
    if any(name in HARD_BLOCKED_FOLDERS for name in parts):
        return True
    # Also block paths that are inside a blacklisted-extension directory (e.g. .app bundles)
    if any(p.suffix.lower() in EXT_BLACKLIST for p in path.parents):
        return True
    return False

def is_blacklisted_extension(path: Path) -> bool:
    return path.suffix.lower() in EXT_BLACKLIST

def is_whitelisted_extension(path: Path) -> bool:
    return path.suffix.lower() in EXT_WHITELIST

# ---------------------------------------------------------
# MAIN SCAN FUNCTION
# ---------------------------------------------------------

def should_skip_dir(dirpath: Path) -> bool:
    """Return True if this directory should not be descended into."""
    if is_hidden(dirpath):
        return True
    if is_symlink(dirpath):
        return True
    if dirpath.name in HARD_BLOCKED_FOLDERS:
        return True
    if dirpath.suffix.lower() in EXT_BLACKLIST:
        return True
    if is_blacklisted(str(dirpath)):
        return True
    if is_project_folder(dirpath):
        return True
    return False


def count_files(folder_path: str) -> int:
    """Quick pre-count of qualifying files using the same filters as scan_folder."""
    root = Path(folder_path).expanduser().resolve()
    count = 0
    for dirpath_str, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirpath = Path(dirpath_str)
        dirnames[:] = [d for d in dirnames if not should_skip_dir(dirpath / d)]
        for filename in filenames:
            path = dirpath / filename
            if is_hidden(path) or is_symlink(path):
                continue
            if is_blacklisted_extension(path):
                continue
            if is_whitelisted_extension(path):
                count += 1
    return count


def scan_folder(folder_path: str, on_progress=None) -> List["FileMetadata"]:
    """
    Walk through a folder recursively and return a list of FileMetadata objects,
    applying blacklist/whitelist rules, skipping system files, hidden files,
    symlinks, dangerous extensions, blacklisted folders, and project folders.

    Uses os.walk with topdown=True so skipped directories are never descended into.
    on_progress(current_file: str, files_scanned: int) is called after each file.
    """

    root = Path(folder_path).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {root}")

    if is_blacklisted(str(root)):
        raise PermissionError(f"Folder is blacklisted and will not be scanned: {root}")

    results: List[FileMetadata] = []
    files_scanned = 0

    for dirpath_str, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirpath = Path(dirpath_str)

        # Prune subdirectories in-place — os.walk won't descend into removed entries
        dirnames[:] = [
            d for d in dirnames
            if not should_skip_dir(dirpath / d)
        ]

        for filename in filenames:
            path = dirpath / filename

            if is_hidden(path) or is_symlink(path):
                continue
            if is_blacklisted_extension(path):
                continue
            if not is_whitelisted_extension(path):
                continue

            try:
                metadata = FileMetadata.from_path(path)
                results.append(metadata)
                files_scanned += 1
                if on_progress:
                    on_progress(str(path), files_scanned)
            except Exception as e:
                print(f"Skipping {path}: {e}")

    return results

