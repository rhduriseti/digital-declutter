# Claire — AI School File Organiser

Claire is a desktop app that helps students automatically organise their school files across local storage and Google Drive using Gemma 3 (local) and Gemma 4 Vision (cloud).

**[Live Demo on Hugging Face Spaces](https://huggingface.co/spaces/rhduriseti/claire-school-organiser)**

---

## How it works

Claire uses a 3-group classification pipeline:

- **Group A** — Filename and folder keywords (instant, no model needed)
- **Group B** — File content keyword scoring (fast, no model needed)
- **Group C** — Gemma AI arbitration for ambiguous files:
  - **Text files** → Gemma 3 (`gemma3:4b`) via Ollama, running fully locally and privately
  - **Image files** → Gemma 4 Vision (`gemma-4-26b-a4b-it`) via Google AI API, for handwritten notes and photos

Files are classified into school subjects (Math, Biology, English, History, Spanish, Art, Band, PE, Science) or personal categories.

---

## Features

- Scans local folders and Google Drive (school + personal accounts)
- Classifies files by subject using Gemma 3 + Gemma 4 Vision
- Detects duplicate files across all sources
- Drag-and-drop to reassign categories
- Click to open files (local) or view in Drive
- Desktop app (Electron) + REST API + Gradio demo

---

## Repo structure

```
declutter_bot/
  api/          # FastAPI server
    routes/     # scan, report, search, drive, files, blacklist, staging
  core/         # Index manager, file metadata, paths
  connectors/   # Local and Google Drive connectors
  tools/        # Classification pipeline, duplicate detection, report generation
  tests/        # 146 pytest tests

frontend/
  src/          # React + Tailwind UI
  electron/     # Electron main + preload (desktop app)

hf_space/       # Self-contained Gradio demo for Hugging Face Spaces

~/.declutter/                  # All user data (outside the repo)
  local_index.json
  gdrive_<name>_index.json
  drive_accounts/              # OAuth tokens
  credentials.json             # Google OAuth (Desktop app type)
  credentials_web.json         # Google OAuth (Web app type)
```

---

## Prerequisites

- Python 3.9+
- Node.js 18+
- [Ollama](https://ollama.com) with `gemma3:4b` pulled (for local text classification)
- `GOOGLE_API_KEY` set in your environment (for Gemma 4 Vision image classification)

```bash
# Pull the local model
ollama pull gemma3:4b

# Set your Google AI API key
export GOOGLE_API_KEY=your_key_here
```

---

## Setup

```bash
git clone https://github.com/rhduriseti/digital-declutter
cd digital-declutter
python -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Running the desktop app

Start the API in one terminal:

```bash
source venv/bin/activate
uvicorn declutter_bot.api.app:app --reload
```

Start the Electron app in a second terminal:

```bash
cd frontend
npm install        # first time only
npm run electron:dev
```

---

## Running the Gradio demo locally

```bash
cd hf_space
pip install -r requirements.txt
python app.py
```

---

## Running tests

```bash
pytest
```

All 146 tests pass. Ollama tests are skipped automatically if Ollama is not running.

---

## Key design decisions

- **Privacy first** — local files never leave the device. Gemma 3 runs fully on-device via Ollama.
- **Gemma 4 Vision for images** — handwritten notes and photos are classified by what Gemma sees, not just the filename.
- **One index per source** — `local_index.json`, `gdrive_school_index.json`, etc. merged at report time.
- **Logout preserves the index** — reconnecting restores the account without rescanning.
- **Student corrections are permanent** — drag-and-drop recategorisation is never overwritten by future scans.

For full architecture details see [ARCHITECTURE.md](ARCHITECTURE.md).
