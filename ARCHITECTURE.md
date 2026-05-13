# Claire — Architecture Document

> Last updated: 2026-05-13
> Target users: High school students (Mac / Windows desktop)

---

## 1. Product Goal

A desktop app that helps high school students organise, deduplicate, and categorise their school files across local storage and Google Drive. Non-destructive by design — students see what can be cleaned up and decide what to do. Nothing is deleted without explicit confirmation.

---

## 2. Target Device Constraint

Most US high school students use **Chromebooks**. This means:
- No local filesystem the user controls
- No `~/Google Drive/` sync folder
- Everything lives in Google Drive natively
- A CLI or desktop app cannot run on ChromeOS natively

**Current deployment:** Desktop app (Electron + React + FastAPI). Chromebook support requires a web app deployment (see Section 13).

---

## 3. Layer Architecture

```
┌──────────────────────────────────────────────┐
│          Student (Electron Desktop App)       │  ← React + Tailwind UI, Vite dev server
│          Gradio Demo (Hugging Face Spaces)    │  ← Public demo, self-contained
├──────────────────────────────────────────────┤
│          FastAPI (REST API)                   │  ← Each tool maps to an endpoint
├───────────────────────┬──────────────────────┤
│    tools/             │    core/              │  ← Business logic
│  categorize_files,    │  index_manager,       │
│  subject_classifier,  │  file_metadata,       │
│  detect_duplicates,   │  paths, utils         │
│  generate_report      │                       │
├───────────────────────┴──────────────────────┤
│          connectors/                          │  ← One per source
│  local.py, gdrive.py                          │
├──────────────────────────────────────────────┤
│          ~/.declutter/                        │  ← All user data, outside the repo
└──────────────────────────────────────────────┘
```

**Electron IPC:** The Electron main process (`electron/main.js`) starts the FastAPI server as a child process, exposes IPC handlers (open file in Finder/Explorer), and proxies API calls via `electron/preload.js` → `contextBridge`.

---

## 4. Connector Architecture

Every file source implements the same interface defined in `connectors/base.py`:

```python
class SourceConnector(ABC):
    source_id: str              # e.g. "local", "gdrive:school", "gdrive:personal"
    def scan() -> list[FileMetadata]
```

| File | Source |
|------|--------|
| `connectors/local.py` | Local filesystem — wraps `scan_folder` |
| `connectors/gdrive.py` | Google Drive — one instance per account |

**Adding a new source = one new file. Core pipeline never changes.**

`gdrive.py` also exposes:
- `get_file_text(file_id, mime_type, max_chars, ext)` — download first N chars for Group B classification
- `get_file_bytes(file_id)` — download full image bytes for Group C Vision classification

---

## 5. Multi-Source Index

Each source has its own JSON file in `~/.declutter/`. They are merged at report time:

| File | Source |
|------|--------|
| `local_index.json` | Local filesystem |
| `gdrive_school_index.json` | Google Drive, school account |
| `gdrive_personal_index.json` | Google Drive, personal account |

Each entry is tagged with its source:

```json
{
  "/Users/student/Documents/bio_notes.pdf": {
    "source": "local",
    "name": "bio_notes.pdf",
    "md5": "abc123",
    "category": "biology",
    "confidence_score": 1.0,
    "classification_group": "A",
    "manually_set": false,
    "duplicate_of": "gdrive:school/1aBcDeFgHiJk"
  },
  "gdrive:school/1aBcDeFgHiJk": {
    "source": "gdrive:school",
    "name": "bio_notes.pdf",
    "md5": "abc123",
    "category": "biology",
    "web_view_link": "https://drive.google.com/file/d/1aBcDeFgHiJk/view"
  }
}
```

**Source field convention:** `"<source_type>:<account_name>"`
- `"local"` — local filesystem
- `"gdrive:school"` — Google Drive, school account
- `"gdrive:personal"` — Google Drive, personal account

**Drive file path convention:** `gdrive:<account>/<file_id>` — e.g. `gdrive:school/1aBcDeFgHiJk`

**Cross-source leakage guard:** `update_index_with_scan` filters incoming data to the current `source_id` before merging, preventing school Drive entries from appearing in the personal Drive index.

---

## 6. Google Drive Integration

### OAuth Strategy
- App credentials (`credentials.json`) downloaded once from Google Cloud Console by the developer
- Stored at `~/.declutter/credentials.json` — never committed to git
- Student's OAuth token saved to `~/.declutter/drive_accounts/<account_name>.json` after browser login
- Token refreshes silently when expired
- **Logout preserves the index** — reconnecting restores the account without rescanning

### Multiple Accounts
Students commonly have two Google accounts (school + personal). The Settings modal in the desktop app lets them connect both:

```
Settings → Connect School Drive  → browser popup → log in → token saved
         → Connect Personal Drive → browser popup → log in → token saved
```

The settings modal polls the popup until it closes to detect OAuth completion.

### Google API Scopes
```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",  # scan files, download for classification
]
```

`drive.readonly` is a non-sensitive scope — significantly easier to pass Google OAuth verification than full `drive` scope.

### MD5 Without Downloading
Drive API returns `md5Checksum` per file for free — no download needed for duplicate detection:
- Local file MD5 computed by reading disk (incremental — only recomputed when `modified_at` changes)
- Drive file MD5 fetched from API at scan time, stored in index

---

## 7. Staging & Safe Delete

All local deletions are two-stage — recoverable first, permanent only on explicit confirmation.

| Action | Local files | Drive files |
|--------|-------------|-------------|
| Safe delete | Move to `~/.declutter_staging/` | Guided — app shows link to open in Drive |
| Recover | Move back from staging | Undo in Drive manually |
| Permanent | `staging empty` → `unlink()` | Student deletes in Drive manually |

Drive files use a guided flow (student opens file in Drive and moves to Trash themselves) because `drive.readonly` scope does not permit writes or deletes.

---

## 8. Subject Classification Pipeline

Three groups run in order. Each group only runs if the previous group did not reach high confidence. Files are processed concurrently (`ThreadPoolExecutor`, max_workers=4).

**Thresholds:**
```python
HIGH_CONFIDENCE = 0.9   # Groups A/B must reach this to skip Gemma
MIN_SCORE_A     = 1     # Group A: at least 1 keyword hit required
MIN_SCORE       = 4     # Groups B+: at least 4 total keyword points required
```

---

### Group A — Metadata only (always runs, no file read)

Scores folder names + filename against the keyword map.

```
score_text(folder_names + filename) → {subject: score}
confidence = winner_score / total_score
```

**Scoring rules:**
- Multi-word phrase match (e.g. "climate change") → 2 points
- Single-word keyword match (e.g. "biology") → 1 point
- Each unique keyword capped at 3 points (prevents repetition bias)
- Tied scores → ambiguous → Group C runs regardless of confidence

**Drive files:** path is an opaque file ID — the actual filename from the index entry is used.

If `confidence >= 0.9` AND `not ambiguous` AND `total_score >= 1` → classification complete (Group A).

---

### Group B — Content keyword scan (local text files + Drive files)

Reads first 500 chars → scores against keyword map. If confidence < threshold, retries with 2000 chars.

```
score_text(first 500 chars)  → confidence ≥ 0.9? → done
                               → try 2000 chars   → confidence ≥ 0.9? → done
                               → else Group C
```

Supported extensions: `.txt .md .pdf .doc .docx .rtf .ppt .pptx .html .htm .csv`

**Local files:** reads directly from disk into memory.

**Drive files:** downloads first 2000 chars transiently via Drive API into memory (never written to disk):
- Google Workspace files (Docs, Slides) → exported as `text/plain`
- Regular files (PDF, DOCX, TXT) → downloaded as binary, decoded as UTF-8

**Privacy:** Drive content is never stored, logged, or sent to any third party during Groups A/B. It exists in process memory only for the duration of classification.

If `confidence >= 0.9` AND `not ambiguous` AND `total_score >= 4` → classification complete (Group B).

---

### Group C — Gemma AI arbitration (text files)

Runs when Groups A and B both fail to reach high confidence. Uses chain-of-thought prompting: document type → student task → class match → decision.

**Returns:** `(subject, confidence, also_could_be)` — runner-up shown in UI when confidence < 0.75.

#### Text path — Gemma 3 via Ollama (primary, fully local)
- Model: `gemma3:4b` via Ollama
- Runs entirely on-device — text content never leaves the machine
- File content (up to 2000 chars) + merged keyword scores from Groups A/B passed as context
- Exponential backoff on errors; falls back to Google AI API if Ollama unavailable

#### Text path — Gemma 4 via Google AI API (fallback)
- Model: `gemma-4-26b-a4b-it` (26B params, 4B active per inference — MoE)
- Used when Ollama is not running or returns an error
- Accessed via `google-genai` Python SDK (`from google import genai`)
- Rate limit: 1,500 req/day, 30 RPM (free tier, no auto-charge on exceeding)
- Exponential backoff on 429 (rate limit), 500 (internal error), and quota errors

**Privacy note:** When Ollama is unavailable, up to 2000 chars of file text are sent to the Google AI API. No PII scrubbing is currently applied before this fallback — production deployment should add a scrubbing step for FERPA/COPPA compliance.

---

### Group C_visual — Gemma 4 Vision (image files)

Triggered for `.jpg .jpeg .png .gif .bmp .webp` files instead of the text Group C path.

- Group A metadata scores used to seed candidate subjects
- **Local images:** file bytes read directly from disk
- **Drive images:** downloaded via `get_file_bytes()` before classification (full image, not preview)
- Image bytes + classification prompt sent to `gemma-4-26b-a4b-it` via Google AI API
- Can classify handwritten notes, whiteboard photos, scanned worksheets
- Falls back to `"media"` if model unavailable or image shows no academic content

**Known performance issue:** Full image bytes are sent without resizing. iPhone photos (5–10 MB) cause slow uploads and 2+ minute classification times for small batches. Fix: resize to max 1024px with Pillow `thumbnail()` before sending.

Audio/video files (`.mp4 .mov .mp3 .wav` etc.) always resolve to `"media"` — no model called.

---

### Final fallback — extension map

If all groups fail (empty content, media file, connection error), the file falls back to `CATEGORY_MAP` in `utils.py`: `.pdf → documents`, `.jpg → images`, `.mp4 → videos`, etc.

---

### What is stored in the index per file

| Field | Description |
|-------|-------------|
| `category` | Classified subject (e.g. "biology", "math") or personal category |
| `confidence_score` | 0.0–1.0 ratio from keyword scoring (0.0 for Group C/Gemma) |
| `classification_group` | Which group classified it: "A", "B", "C", "C_visual", "extension", "fallback" |
| `also_could_be` | Runner-up subject from Gemma (Group C/C_visual only, shown in UI) |
| `manually_set` | `true` if student corrected — pipeline never overwrites this |
| `categorised_modified_at` | `modified_at` value at last classification — used to skip unchanged files |

---

### Incremental categorisation

| Condition | Action |
|-----------|--------|
| `manually_set = true` | Never reclassify — student's choice is permanent |
| `category` set + `modified_at` unchanged | Skip — reuse existing category |
| `category` set + `modified_at` changed | Re-categorise — file may have changed |
| No `category` (new file) | Categorise and store result |

---

### Model selection rationale

| Path | Model | When used |
|------|-------|-----------|
| Text classification (primary) | `gemma3:4b` via Ollama | Ollama running locally |
| Text classification (fallback) | `gemma-4-26b-a4b-it` via Google AI API | Ollama unavailable |
| Image classification | `gemma-4-26b-a4b-it` via Google AI API | Always (no local vision model available) |

**Why Gemma 3 locally for text:** Fast (~1–2s/file), free, fully private — text content never leaves device.
**Why Gemma 4 Vision for images:** Previous Gemma generations are text-only. Gemma 4 is the first Gemma with confirmed multimodal capability. The 26B MoE model with 4B active params is fast and cost-efficient on the free API tier.

---

## 9. Duplicate Detection

### Detection levels implemented

| Level | Method | Local | Drive |
|-------|--------|-------|-------|
| 1a | MD5 exact match | ✅ | ✅ Free from API |
| 1b | Filename similarity (fuzzy string match) | ✅ | ✅ |
| 1c | File size filter (±10%) | ✅ | ✅ |

**Why Drive files can't use deeper levels:**
`drive.readonly` returns metadata only — name, size, MD5, webViewLink. Reading file content requires downloading, which is slow and hits API quota.

### Detection logic
```
Same MD5                      → exact duplicate (certain)
Similar name + same size      → very likely duplicate (flag for review)
Similar name + size ±10%      → possible duplicate (show to student)
```

### Performance: incremental MD5

| File type | MD5 source | When recomputed |
|-----------|-----------|-----------------|
| Local (unchanged) | Stored in index | Never — `modified_at` unchanged |
| Local (new or modified) | Read from disk | When `modified_at` changes |
| Drive | Stored in index from API | Never — Drive API provides it free |

---

## 10. Data Storage

**JSON files in `~/.declutter/`** (outside the repo — persists across reinstalls)

| File | Contents |
|------|----------|
| `local_index.json` | Index of local files |
| `gdrive_<name>_index.json` | Index per connected Drive account |
| `blacklist.json` | Folders excluded from scanning |
| `staging_log.json` | Soft-deleted local files |
| `credentials.json` | Google OAuth credentials (Desktop app type, never committed) |
| `credentials_web.json` | Google OAuth credentials (Web app type, never committed) |
| `drive_accounts/<name>.json` | Per-account OAuth tokens |

---

## 11. Organised View

The React UI (`frontend/src/pages/OrganisedFiles.jsx`) shows files grouped by subject across all connected sources.

**Per file:**
- Clickable: local files open in Finder/Explorer via Electron IPC (`shell:openFile`); Drive files open `web_view_link` in browser
- Source badge (local / school / personal)
- Duplicate badge (⚠️) when `duplicate_of` is set
- `also_could_be` note when Gemma had a runner-up

**Drag-and-drop reassignment:**
- Student can drag a file to a different subject — sets `manually_set=true` in the index
- Manual corrections are permanent — never overwritten by future scans

**Drive file size display:** Drive files without a local size show "Drive file" rather than a size, since size is not always returned by the API.

---

## 12. UI Design

**Current implementation: React + Tailwind + Electron (desktop app)**

| Page | Purpose |
|------|---------|
| `Onboarding.jsx` | First-run setup — select local folders, connect Drive accounts |
| `Dashboard.jsx` | Scan trigger, progress, summary stats, Settings modal |
| `OrganisedFiles.jsx` | Files grouped by subject, drag-and-drop, open files |

**Settings modal (Dashboard.jsx):**
- Connect / disconnect Google Drive accounts (school + personal)
- OAuth flow: opens a popup window, polls until popup closes, then re-fetches accounts
- Polled every 2 seconds while popup is open

**Gradio demo (`hf_space/app.py`):**
- Self-contained Gradio app for public demo on Hugging Face Spaces
- Syncs the same classifier files from the main repo
- Uses Google AI API only (no Ollama) for simplicity in the demo environment

---

## 13. Product Tiers

---

### Tier 1 — Claire (Current — Hackathon Build)

**Target:** High school students, parents, schools
**Value:** Organised files, duplicate detection, space savings

| Feature | Status |
|---------|--------|
| Subject classification (3-group pipeline: A/B/Gemma) | ✅ Built |
| Local file scanning + indexing | ✅ Built |
| Google Drive scan (school + personal) | ✅ Built |
| MD5 duplicate detection (cross-source) | ✅ Built |
| Image classification via Gemma 4 Vision | ✅ Built |
| Staging / safe delete (local) | ✅ Built |
| Organised view with drag-and-drop reassignment | ✅ Built |
| FastAPI REST layer | ✅ Built |
| Electron + React desktop app | ✅ Built |
| Gradio demo on Hugging Face Spaces | ✅ Built |
| 146 pytest tests | ✅ Built |
| Image resizing before Vision API call | ⚠️ Needed (see notes) |
| PII scrubbing before cloud text fallback | ⚠️ Needed for production |

---

### Tier 2 — AI Study Assistant (Planned)

**Value:** AI that knows your entire school life, helps you study, keeps you on top of deadlines

| Feature | Description |
|---------|-------------|
| **Semantic search** | "Show my biology notes from last month" — LanceDB local vector DB |
| **Study guide generation** | RAG over indexed files → Gemma generates subject-specific guide |
| **Near-duplicate detection** | Catches essay_v1 vs essay_v2, PDF export of Word doc |
| **Video classification** | Frame extraction + Gemma 4 Vision |
| **Google Classroom** | Assignment due dates, course names, teacher feedback, grades |
| **Google Calendar** | School events, exam schedule, project deadlines |
| **Email digest** | Weekly summary: upcoming assignments, new feedback, suggested study topics |
| **Gmail integration** | School-only emails (@school.edu domain), local Gemma 3 extraction |

**LanceDB note:** Runs fully locally, fits the privacy-first design. Embeds all indexed files; on study guide request, retrieves top-k semantically similar files and feeds them into Gemma 3 as context.

---

### Tier 3 — Web App Deployment (Planned)

**Target:** Schools deploying to Chromebook users (no desktop app install possible)

| Component | Approach |
|-----------|----------|
| Gemma 3 text | EC2 `g4dn.xlarge` (GPU) or `t3.xlarge` (CPU) running Ollama — keeps text off third-party APIs |
| Gemma 4 Vision | Google AI API — images only (fewer calls, acceptable for FERPA if image-only) |
| Data residency | Specific AWS region for FERPA compliance |
| Auth | OAuth tokens per student, stored server-side |
| Storage | Per-student indexes in S3 or RDS |

---

## 14. Build Order

**Phase 1 — Tier 1 (complete)**
1. ~~Subject classification pipeline (Groups A + B + C)~~ ✅
2. ~~Connector architecture + Google Drive connector~~ ✅
3. ~~Multi-source index (per-source JSON files)~~ ✅
4. ~~Incremental categorisation + MD5 computation~~ ✅
5. ~~FastAPI REST layer~~ ✅
6. ~~Electron + React desktop app~~ ✅
7. ~~Gemma 4 Vision for image classification~~ ✅
8. ~~Drive image Vision classification~~ ✅
9. ~~146 pytest tests~~ ✅
10. ~~Gradio demo on Hugging Face Spaces~~ ✅
11. Image resizing before Vision API call (cap at 1024px)
12. PII scrubbing before Google AI API text fallback

**Phase 2 — Tier 2 (AI Study Assistant)**
13. LanceDB local vector index — embed files as they are indexed
14. Semantic search via LanceDB
15. Study guide generation (RAG + Gemma 3)
16. Near-duplicate detection (text extraction + difflib/simhash)
17. Video frame extraction + classification (ffmpeg + Gemma 4 Vision)
18. Google Classroom API integration
19. Google Calendar API integration
20. Gmail digest (school-only, local Gemma extraction)

**Phase 3 — Tier 3 (Web App)**
21. EC2 + Ollama deployment for Gemma 3 text classification
22. Per-student auth + index storage
23. Chromebook web UI

---

## 15. Testing

```bash
pytest                           # run all 146 tests
pytest -k "not ollama"           # skip Ollama tests (if Ollama not running)
```

Ollama tests are automatically skipped if Ollama is not running. Google AI API tests use mocked responses — no API key required to run tests.

Test coverage:
- Group A/B/C classification (text + visual)
- Index manager (merge, update, cross-source isolation)
- Drive connector (scan, get_file_text, get_file_bytes)
- FastAPI routes (scan, report, search, drive, files, blacklist, staging)
- Duplicate detection
- Staging manager

---

## 16. Privacy Design

| Data | Where it stays |
|------|---------------|
| Local file content (Group B) | Process memory only — never written, logged, or sent |
| Local file content (Group C, Ollama running) | On-device — Gemma 3 runs locally, never leaves machine |
| Local file content (Group C, Ollama unavailable) | Sent to Google AI API (up to 2000 chars) — no PII scrubbing yet |
| Drive file content (Group B) | Process memory only — downloaded transiently for classification |
| Drive file content (Group C) | Same as local Group C rules above |
| Drive images (Group C_visual) | Full image bytes sent to Google AI API |
| Index files | Stay in `~/.declutter/` — contain filenames, sizes, MD5s, categories. No file content. |
| OAuth tokens | Stay in `~/.declutter/drive_accounts/` — never committed to git |
