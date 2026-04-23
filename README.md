# Digital Declutter

A tool that helps students organise, categorise, and clean up files across local storage and Google Drive.

---

## What it does

- Scans local folders and Google Drive accounts
- Categorises files by subject (Biology, Math, English, etc.)
- Detects duplicate files across all sources
- Lets you remove duplicates, untrack folders, and manage a blacklist
- Exposes everything as a CLI and a REST API (for the web UI)

---

## Repo structure

```
declutter_bot/
  cli/          # CLI entry point (declutter command)
  api/          # FastAPI server (declutter-api command)
    routes/     # One file per feature: scan, report, search, drive, untrack, blacklist, staging
  core/         # Shared logic: index manager, file metadata, paths, blacklist, staging
  connectors/   # Local and Google Drive connectors
  tools/        # Business logic: scan, categorise, detect duplicates, delete, search, report
  tests/        # Pytest test suite

~/.declutter/                  # All user data lives here (outside the repo)
  local_index.json             # Index of local files
  gdrive_<name>_index.json     # Index per connected Drive account
  drive_accounts/              # OAuth tokens per account
  credentials.json             # Google OAuth credentials for CLI (Desktop app type)
  credentials_web.json         # Google OAuth credentials for API (Web app type)
  blacklist.json
  staging_log.json
```

---

## Setup

**Requires Python 3.9+**

```bash
# Clone and set up a virtual environment
git clone <repo-url>
cd digital_declutter
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

---

## Running the CLI

```bash
# Scan a local folder
declutter scan ~/Documents

# Scan a connected Google Drive account
declutter scan --source gdrive:school

# View report across all sources
declutter report --pretty

# Search the index
declutter search "bio notes"

# Connect a Google Drive account (opens browser)
declutter drive-login school

# Disconnect (token deleted, index preserved)
declutter drive-logout school

# List connected accounts
declutter drive-accounts

# Remove a folder from the index (without blacklisting)
declutter untrack ~/Documents/some-folder

# Blacklist a folder permanently
declutter blacklist add ~/Downloads/some-folder

# Delete duplicate files
declutter delete-duplicates --dry-run
declutter delete-duplicates

# Manage staged (soft-deleted) files
declutter staging show
declutter staging restore --all
declutter staging empty
```

---

## Running the API server

```bash
declutter-api
# API runs at http://127.0.0.1:8000
# Swagger docs at http://127.0.0.1:8000/docs
```

The API exposes the same features as the CLI. Ronit's web UI talks to this server.

For Google Drive OAuth via the API, you need a **Web application** OAuth client saved as `~/.declutter/credentials_web.json`. The CLI uses a **Desktop app** client saved as `~/.declutter/credentials.json`. These are different credentials — see Google Cloud Console to create them.

---

## Running tests

```bash
pytest
```

Ollama tests are skipped automatically if the Ollama server is not running. All other tests run without any external dependencies.

---

## Key design decisions

- **One index file per source** — `local_index.json`, `gdrive_school_index.json`, etc. Report and search merge them automatically.
- **Logout preserves the index** — only the OAuth token is deleted. Reconnecting restores the account without rescanning.
- **Blacklist vs untrack** — blacklist permanently blocks a folder from future scans; untrack just removes its current entries (folder can be scanned again later).
- **Drive files are never deleted by the app** — only local files can be moved to staging or permanently deleted. Drive duplicates show a link to delete manually.
- **Privacy first** — local file content never leaves the device. For Google Drive files, content is downloaded transiently into memory for classification and discarded immediately — never stored on disk or sent to any third party.

For full architecture details see [ARCHITECTURE.md](ARCHITECTURE.md).
