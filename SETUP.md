# Claire — Setup & Deployment Guide

> Last updated: 2026-05-06

---

## Repo Overview

Claire is split across three repos:

| Repo | What it is |
|---|---|
| `digital_declutter` | Desktop monorepo — Python FastAPI backend + React/Electron frontend. Runs entirely on the user's machine. No cloud required. |
| `claire-app` | Web + Electron frontend. Works in a browser (with Firebase Auth) or as an Electron desktop client pointing at `digital_declutter`'s backend. |
| `claire-api` | Cloud backend only. Deployed to Cloud Run. Requires Firebase Auth. No local file access. |

---

## Deployment Options

### Option 1 — Web app + cloud LLM
- Frontend: `claire-app` (browser, deployed to Firebase Hosting)
- Backend: `claire-api` (Cloud Run)
- LLM: Gemini API (remote)
- Use case: Production web product. No local install required.

### Option 2 — Desktop client + local backend + local LLM *(current working desktop mode)*
- Frontend: `claire-app` (Electron) or `digital_declutter/frontend` (Electron)
- Backend: `digital_declutter` FastAPI (running locally on `localhost:8000`)
- LLM: Gemma via Ollama (local)
- Use case: Desktop app. Works offline. Can scan local files.

### Option 3 — Fully bundled desktop app *(Kaggle submission target)*
- Everything in `digital_declutter`: Electron frontend + FastAPI backend spawned by Electron on startup
- LLM: Gemma 4 via Ollama (must be pre-installed; model weights cannot be bundled)
- Use case: Single-app install for end users. Electron owns the backend lifecycle.
- Status: Backend and frontend work separately today; auto-spawning the backend from `electron/main.js` is the remaining bundling work.

### Option 4 — Shared backend, multiple clients
- Backend: `digital_declutter` FastAPI running on one machine in the network (e.g. a Mac Mini or dev server)
- Frontend: Electron or browser client on any machine pointing at the backend's IP
- LLM: Gemma via Ollama on the backend machine
- Use case: Lab or classroom setup — one beefy machine runs the backend and Ollama, thin clients connect to it.
- **Constraint:** Local file scanning scans files on the machine the *backend* runs on, not the client. For a user to scan their own local files, the backend must run on their machine. Drive scanning works from any machine since it's all API calls.
- **To configure:** Change `API` in `frontend/src/config.js` from `http://localhost:8000` to the backend machine's IP, e.g. `http://192.168.1.50:8000`.

---

## Frontend vs Backend Relationship

```
claire-app (browser)       →  claire-api (Cloud Run)         [Option 1]
claire-app (Electron)      →  digital_declutter backend      [Option 2]
digital_declutter frontend →  digital_declutter backend      [Option 2/3]
any machine on network     →  digital_declutter backend      [Option 4]
```

`claire-app`'s Electron mode detects `window.electron.isElectron`, skips Firebase Auth, and points to `localhost:8000`. Long-term, `digital_declutter/frontend` can be retired in favour of `claire-app`'s Electron mode — they are diverged copies of the same UI.

**Why Electron cannot use `claire-api`:** `claire-api` runs in the cloud and cannot access files on the user's local machine. Local file scanning requires a backend that runs on the user's machine.

---

## Kaggle / Desktop Setup (Option 2)

### Prerequisites

1. **Python 3.11+** — [python.org](https://python.org)
2. **Node.js 18+** — [nodejs.org](https://nodejs.org)
3. **Ollama** — [ollama.com](https://ollama.com) or `brew install ollama` on Mac
4. **Gemma 4 model** — after installing Ollama:
   ```bash
   ollama pull gemma3
   ```

### Google Drive (optional)

Drive scanning requires Google OAuth app credentials. These identify the *app* to Google (not the user) and should be bundled with the repo for judges.

Place the file at:
```
~/.declutter/credentials.json
```

Without this file, the app works for local file scanning only. Drive scanning will be unavailable but everything else runs normally.

For a production distribution, `credentials.json` would be bundled inside the app binary so users never need to handle it manually.

### Setup

```bash
# Clone the repo
git clone <repo-url>
cd digital_declutter

# Python backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e .

# Frontend
cd frontend
npm install
cd ..
```

### Running the App

Open three terminals:

```bash
# Terminal 1 — Ollama (local LLM)
ollama serve

# Terminal 2 — Python backend
source venv/bin/activate
uvicorn declutter_bot.api.app:app
# Backend running at http://localhost:8000

# Terminal 3 — Electron frontend
cd frontend
npm run electron:dev
```

The Electron window opens and connects to the backend automatically.

### Running Tests

```bash
source venv/bin/activate
pytest declutter_bot/tests/ --ignore=declutter_bot/tests/test_ollama_response.py
```

`test_ollama_response.py` requires Ollama to be running at import time and is excluded from the standard suite. All other tests (109) run without Ollama.

---

## Bundling for Distribution (future work)

To ship as a single app that users just open:

1. **Compile the Python backend** with PyInstaller into a standalone binary — no Python install required on the user's machine
2. **Update `electron/main.js`** to spawn the backend binary on app start and kill it on quit
3. **Package with `electron-builder`** to produce `.dmg` (macOS) or `.exe` (Windows)
4. **Bundle `credentials.json`** inside the binary so users don't need to obtain it manually

Ollama and the Gemma model must still be installed separately — model weights are 4–9 GB and cannot be bundled. The app should detect whether Ollama is running on startup and guide the user if not.

---

## Data Storage

All user data lives in `~/.declutter/`:

| File | Contents |
|---|---|
| `local_index.json` | Index of scanned local files |
| `gdrive_<name>_index.json` | Index per connected Drive account |
| `drive_accounts/<name>.json` | OAuth tokens per Drive account |
| `credentials.json` | Google OAuth app credentials (never committed to git) |

Nothing is written outside `~/.declutter/` except files the user explicitly archives, which are moved to `~/.declutter_staging/` for safe recovery.
