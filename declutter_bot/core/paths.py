from pathlib import Path

# All user data lives in ~/.declutter/ — persists across reinstalls and project moves
DATA_DIR = Path.home() / ".declutter"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BLACKLIST_PATH = DATA_DIR / "blacklist.json"
STAGING_LOG_PATH = DATA_DIR / "staging_log.json"
DRIVE_ACCOUNTS_DIR = DATA_DIR / "drive_accounts"
GOOGLE_CREDENTIALS_PATH = DATA_DIR / "credentials.json"
GOOGLE_WEB_CREDENTIALS_PATH = DATA_DIR / "credentials_web.json"


def get_index_path(source_id: str) -> Path:
    """
    Returns the index file path for a given source.
    source_id examples: "local", "gdrive:school", "gdrive:personal", "gmail:school"

    local              → ~/.declutter/local_index.json
    gdrive:school      → ~/.declutter/gdrive_school_index.json
    gdrive:personal    → ~/.declutter/gdrive_personal_index.json
    gmail:school       → ~/.declutter/gmail_school_index.json
    """
    if source_id == "local":
        return DATA_DIR / "local_index.json"
    name = source_id.replace(":", "_") + "_index.json"
    return DATA_DIR / name


def get_expanded_map_path(source_id: str) -> Path:
    """
    Returns the expanded map path for a given source.
    local files use local expanded map.
    All drive/gmail accounts share a per-account expanded map.
    """
    if source_id == "local":
        return DATA_DIR / "local_expanded_map.json"
    name = source_id.replace(":", "_") + "_expanded_map.json"
    return DATA_DIR / name
