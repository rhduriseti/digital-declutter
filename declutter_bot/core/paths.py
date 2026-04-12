from pathlib import Path

# All user data lives in ~/.declutter/ — persists across reinstalls and project moves
DATA_DIR = Path.home() / ".declutter"
DATA_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = DATA_DIR / "index.json"
BLACKLIST_PATH = DATA_DIR / "blacklist.json"
STAGING_LOG_PATH = DATA_DIR / "staging_log.json"
EXPANDED_MAP_PATH = DATA_DIR / "expanded_map.json"
DRIVE_ACCOUNTS_DIR = DATA_DIR / "drive_accounts"
GOOGLE_CREDENTIALS_PATH = DATA_DIR / "credentials.json"
