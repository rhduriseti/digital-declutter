# Digital Declutter — Architecture Document

> Last updated: 2026-04-13
> Target users: High school students (primarily Chromebook, some Windows/Mac)

---

## Confirmed Architecture (2026-04-13)

### Core Principle: Unified Archive Workflow

Same "Archive" action for all sources — automatic for local files, guided for Drive files.
The word "Archive" is consistent everywhere. The mechanism differs under the hood but the student never needs to understand that.

### Organised View (App-Only)

Files are shown organised by subject in the app. This view exists only in the app's index — nothing is written to disk, no symlinks created, no Drive shortcuts created:

```
App UI / CLI (organised view)        Real files (untouched)
─────────────────────────────        ──────────────────────
Biology/                             ~/Documents/bio_notes.pdf
  bio_notes.pdf    [Show in Finder]  ~/Documents/cell_structure.pdf
  cell_structure.pdf                 Google Drive/Bio Notes.pdf
  Bio Notes.pdf    [Open in Drive]

Math/
  calc_test.pdf    [Open in Drive]   Google Drive/calc_test.pdf
```

Same experience across all sources and all devices — Chromebook, Mac, Windows.
Auto-scan on app open if index is stale — no "organise" button needed.

### Unified Archive Flow

```
Duplicates found — 45 MB recoverable

┌─────────────────────────────────────────────┐
│ bio_notes.pdf  (3 copies)                   │
│                                             │
│ ● bio_notes.pdf        local   [Archive]    │
│ ● Bio Notes.pdf        school  [Archive]    │
│ ● bio notes copy.pdf   personal [Archive]   │
└─────────────────────────────────────────────┘
         [ Archive All Duplicates ]
```

| Source | What "Archive" does |
|--------|-------------------|
| Local | App automatically moves to `~/.declutter_staging/` (recoverable) |
| Drive | App shows "This file is in Google Drive. Click to open and move to Archive folder" |

- Same button, same word, same mental model for student
- Local is automatic (better UX where possible)
- Drive is guided (honest about current permission limitation)
- If full `drive` scope is verified later → Drive becomes automatic too, zero UI change needed

### School Sales Story

- App identifies duplicate files across all student accounts
- Moves/guides to archive → frees up Google Workspace storage
- Storage costs real money at scale → clear ROI for school IT admins
- School IT admin is the **buyer**, students are the **users**

### Google OAuth Scope Strategy

- **Now:** `drive.readonly` for scanning + guided archive flow
- **Later (after verification):** full `drive` scope → Drive archive becomes automatic
- Verification is easier with a working product and real school usage to show Google

### Auto-Scan Behaviour
- App opens → checks if index older than X hours → auto-scans in background
- Student opens app → organised view is just there, no buttons needed
- Manual refresh button as escape hatch
```

Student does the actual deletion. App never does it for them.

### CLI Organised View

The CLI shows the same organised view as a Rich table:

```
┌──────────────┬───────────────────────┬────────┬──────────┐
│ Subject      │ File                  │ Source │ Size     │
├──────────────┼───────────────────────┼────────┼──────────┤
│ Biology      │ bio_notes.pdf         │ local  │ 12 MB    │
│              │ Bio Notes.pdf         │ school │ 12 MB ⚠️ │
├──────────────┼───────────────────────┼────────┼──────────┤
│ Math         │ calc_test.pdf         │ school │ 8 MB     │
└──────────────┴───────────────────────┴────────┴──────────┘
⚠️  6 duplicates — 45 MB recoverable
    Run: declutter duplicates --guide   to see how to free space
```

CLI, API, and UI all show the same organised view — just rendered differently.

### Why This Is Better

| Concern | Current design | Safer design |
|---------|---------------|--------------|
| Google OAuth scope | `drive` (sensitive, hard to verify) | `drive.readonly` (non-sensitive, easy to verify) |
| Google verification wait | Weeks, can be rejected | Days, rarely rejected |
| Risk to student files | Some (staging, trash) | Zero — app never touches files |
| Windows symlink issue | Blocked by school IT | Irrelevant — nothing written to disk |
| Chromebook support | Limited | Full |
| School IT trust | Moderate | High — read-only is easy to justify |
| Staging manager complexity | High (Drive-aware) | Low — local only, or removed |
| Connector interface | scan + trash + untrash + delete | scan only |

### What Changes in Code

| Component | Change |
|-----------|--------|
| `SourceConnector` base class | Remove `trash/untrash/permanent_delete` — `scan()` only |
| `gdrive.py` | Remove trash/untrash/delete methods |
| `staging_manager.py` | Remove Drive-aware logic, local only |
| `delete_duplicates.py` | Remove Drive routing |
| `generate_report` | Add subject-grouped organised view rendering |
| `FileMetadata` | Add `web_view_link` field for Drive files |
| Drive API fields | Add `webViewLink` to fields fetch |

### What Stays the Same

- Local staging (move to `~/.declutter_staging/`) — kept for explicit local deletes
- All subject classification — unchanged
- MD5 duplicate detection — unchanged
- Multi-source index — unchanged
- `--source` flag on CLI commands — unchanged

---

---

## 1. Product Goal

A tool that helps high school students organise, deduplicate, and categorise their school files across local storage and Google Drive. Non-destructive by design — students see what can be cleaned up and decide what to do. Nothing is deleted without explicit confirmation.

---

## 2. Target Device Constraint

Most US high school students use **Chromebooks**. This means:
- No local filesystem the user controls
- No `~/Google Drive/` sync folder
- Everything lives in Google Drive natively
- A CLI or desktop app cannot run on ChromeOS

**Consequence:** The student-facing product must be a **web app** running on a server that calls the Drive API on their behalf. The CLI remains a developer/admin tool and the foundation the web API is built on.

---

## 3. Layer Architecture

```
┌─────────────────────────────────────────┐
│           Student (Browser)             │  ← Streamlit first, then PyQt6/Tauri
├─────────────────────────────────────────┤
│           FastAPI (Web API)             │  ← Each CLI command maps to an endpoint
├─────────────────────────────────────────┤
│           CLI (declutter)               │  ← Developer/admin tool, drives automation
├────────────────────┬────────────────────┤
│    tools/          │    core/            │  ← Business logic, never changes
│  scan, report,     │  index, staging,    │
│  categorise,       │  blacklist,         │
│  detect_dupes      │  paths, utils       │
├────────────────────┴────────────────────┤
│           connectors/                   │  ← One per source (local, gdrive, gmail...)
├─────────────────────────────────────────┤
│           ~/.declutter/                 │  ← All user data, persists across reinstalls
└─────────────────────────────────────────┘
```

---

## 4. Connector Architecture

Every file source (local disk, Google Drive, Gmail, Dropbox) implements the same interface defined in `connectors/base.py`:

```python
class SourceConnector(ABC):
    source_id: str              # e.g. "local", "gdrive:school", "gdrive:personal"
    def scan() -> list[FileMetadata]
    def trash(file_id) -> bool
    def untrash(file_id) -> bool
    def permanent_delete(file_id) -> bool
```

| File | Source |
|------|--------|
| `connectors/local.py` | Local filesystem — wraps `scan_folder` |
| `connectors/gdrive.py` | Google Drive — one instance per account |
| `connectors/gmail.py` | Gmail attachments (future) |
| `connectors/dropbox.py` | Dropbox (future) |

**Adding a new source = one new file. Core pipeline never changes.**

---

## 5. Multi-Source Index

All sources share a single `~/.declutter/index.json`. Each entry is tagged with its source:

```json
{
  "files": {
    "/Users/student/Documents/bio_notes.pdf": {
      "source": "local",
      "name": "bio_notes.pdf",
      "md5": "abc123",
      "duplicate_of": "gdrive:school/1aBcDeFgHiJk"
    },
    "gdrive:school/1aBcDeFgHiJk": {
      "source": "gdrive:school",
      "name": "bio_notes.pdf",
      "md5": "abc123",
      "duplicate_of": null
    }
  }
}
```

**Source field convention:** `"<source_type>:<account_name>"`
- `"local"` — local filesystem
- `"gdrive:school"` — Google Drive, school account
- `"gdrive:personal"` — Google Drive, personal account
- `"gmail:school"` — Gmail (future)

**Drive file path convention:** `gdrive:<account>/<file_id>`
- e.g. `gdrive:school/1aBcDeFgHiJk`
- Single slash — double slash is collapsed by Python's `Path()`

**This naming convention is set in stone once Drive data enters the index — cannot be changed without a migration.**

---

## 6. Google Drive Integration

### OAuth Strategy
- App credentials (`credentials.json`) downloaded once from Google Cloud Console by the developer
- Stored at `~/.declutter/credentials.json` — never committed to git
- Student's OAuth token saved to `~/.declutter/drive_accounts/<account_name>.json` after browser login
- Token refreshes silently when expired

### Multiple Accounts
Students commonly have two Google accounts (school + personal):
```bash
declutter drive-login school      # browser opens → log in with school@schoolname.edu
declutter drive-login personal    # browser opens → log in with personal@gmail.com
```

### Google API Scope Decision
**We use the minimum scopes needed:**

```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",  # scan files
    "https://www.googleapis.com/auth/drive.file",       # create shortcuts only
]
```

**Why not full `drive` scope:**
- Full Drive scope triggers heavy Google OAuth verification scrutiny
- `readonly` + `drive.file` are non-sensitive — significantly easier to verify
- Aligns with non-destructive design philosophy

### Non-Destructive Design (Shortcut Approach)
Instead of moving or deleting files, the app creates **Drive shortcuts** (symlinks) in an organised folder structure:

```
My Drive/
  Organised by Declutter/
    Biology/
      → Bio Notes.pdf        (shortcut to original)
      → Cell Structure.pdf   (shortcut to original)
    Math/
      → Calc Test 2.pdf      (shortcut to original)
```

- Original files are never touched
- Students get an organised view without risk
- Duplicates are reported, not deleted — student decides manually
- Shortcut creation uses `drive.file` scope (files the app creates)

### MD5 Without Downloading
Drive API returns `md5Checksum` for free per file — no download needed. This enables cross-source duplicate detection:
- Local file MD5 computed by reading disk
- Drive file MD5 fetched from API at scan time, stored in index
- `detect_duplicates` uses whichever is available

### Google Verification Path
- **Development / small rollout:** Add up to 100 Gmail addresses as test users manually — no verification needed
- **School rollout (recommended):** School IT admin adds app to Google Workspace — all `@schoolname.edu` accounts work automatically, bypasses public verification
- **Public release:** Submit for OAuth verification — requires privacy policy, homepage, and Google review (1-4 weeks)

---

## 7. Staging & Safe Delete

All deletions are two-stage — recoverable first, permanent only on explicit confirmation.

| Action | Local files | Drive files |
|--------|-------------|-------------|
| Safe delete | Move to `~/.declutter_staging/` | `files.trash()` — recoverable 30 days |
| Recover | `staging restore` → moves back | `staging restore` → calls `untrash()` |
| Permanent | `staging empty` → `unlink()` | `staging empty` → `files.delete()` |

Both local and Drive entries are logged in `staging_log.json` with a `source` field. The `staging show/restore/empty` commands work uniformly across both.

---

## 8. Subject Classification Pipeline

Three groups run in order. Each group only runs if the previous group did not reach high confidence.

---

### Group A — Metadata only (always runs, no file read)

Scores folder names + filename against the seed map and expanded map.

```
score_text(folder_names + filename) → {subject: score}
confidence = winner_score / total_score
```

**Scoring rules:**
- Multi-word phrase match (e.g. "climate change") → 2 points
- Single-word keyword match (e.g. "biology") → 1 point
- Each unique keyword capped at 3 points (prevents repetition bias)
- Tied scores → confidence capped at 0.3 → next group runs

**Thresholds:**
```
confidence ≥ 0.7  → done (high confidence)
confidence ≥ 0.4  → try Group B
confidence < 0.4  → skip to Group C
scores all zero   → skip to Group C
```

**Drive files:** path is an opaque file ID — the actual filename from the index entry is used instead.

---

### Group B — Content keyword scan (local text files + Drive files)

Reads first 500 chars → scores against seed map + expanded map.
If 0.4 ≤ confidence < 0.7 → tries 2000 chars.

```
score_text(first 500 chars) → confidence
  ≥ 0.7 → done
  ≥ 0.4 → try 2000 chars → done if ≥ 0.4
  < 0.4 → Group C
```

**Local files:** reads directly from disk into memory.

**Drive files:** downloads first 2000 chars transiently via Drive API into memory (never written to disk):
- Google Workspace files (Docs, Slides) → exported as `text/plain`
- Regular files (PDF, DOCX, TXT) → downloaded as binary, decoded as UTF-8

**Privacy:** Drive content is never stored, logged, or sent to any third party. It exists in process memory only for the duration of classification, then is discarded.

**Skipped for:** media files (.jpg, .mp4, .mp3, etc.) — content reading has no value.

---

### Group C — Semantic similarity via sentence-transformers

Runs when Groups A and B both fail to reach medium confidence.
Uses `all-MiniLM-L6-v2` to compute cosine similarity between file content and subject descriptions built from the seed map keywords.

```
text_embedding ←→ subject_description_embeddings
→ picks subject with highest cosine similarity
→ always returns a subject (never falls through)
→ saves new keywords to expanded map if confidence > 0.5
```

**Local files:** reads first 2000 chars from disk.
**Drive files:** same transiently downloaded content as Group B.
**Media files:** skipped (no text content).

Model is loaded once and cached for the session — first call takes ~5–10 seconds.

---

### Ollama fallback (when sentence-transformers unavailable)

If `sentence-transformers` is not installed, Ollama (gemma3:4b) is used as Group C fallback.
Skipped for media files. When Ollama classifies with confidence ≥ 0.85, new keywords are saved to the expanded map.

---

### Final fallback — extension map

If all groups fail (empty content, media file, connection error), the file falls back to the extension-based `CATEGORY_MAP` in `utils.py`:
`.pdf → documents`, `.jpg → images`, `.mp4 → videos`, etc.

---

### What is stored in the index per file

| Field | Description |
|-------|-------------|
| `category` | Classified subject (e.g. "biology", "math") |
| `confidence_score` | 0.0–1.0 ratio from scoring (0.0 for Group C/Ollama) |
| `classification_group` | Which group classified it: "A", "B", "C", "ollama", "fallback" |
| `manually_set` | `true` if student corrected — pipeline never overwrites this |
| `categorised_modified_at` | Timestamp when last categorised — used to skip unchanged files |

---

### Category sources

| Source | Description |
|--------|-------------|
| **Seed map** (`utils.py`) | ~20 subjects, ~300 keywords. Fixed. Your daughter maintains this. |
| **Expanded map** (`~/.declutter/*_expanded_map.json`) | Auto-learned keywords from Groups C and Ollama. Grows over time. One file per source. |
| **Personal categories** (V2) | Student-created categories (e.g. "AP Literature", "Drama"). Stored in Drive appdata. |

---

### Incremental categorisation

Files are only re-categorised when necessary:

| Condition | Action |
|-----------|--------|
| `manually_set = true` | Never reclassify — student's choice is permanent |
| `category` set + `modified_at` unchanged | Skip — reuse existing category |
| `category` set + `modified_at` changed | Re-categorise — file may have changed |
| No `category` (new file) | Categorise and store result |

---

### Planned: Multimodal classification (Tier 2)

Current pipeline is text-only. Images and video fall back to the extension map.

| Type | Plan |
|------|------|
| Images | LLaVA via Ollama (free, local) or Claude API |
| Video | Extract 3–5 frames with `ffmpeg`, pass to LLaVA or Gemini |

---

## 9. Duplicate Detection

### Detection levels

| Level | Method | Local | Drive | Cost |
|-------|--------|-------|-------|------|
| 1a | MD5 exact match | ✅ | ✅ Free from API | Zero |
| 1b | Filename similarity (fuzzy string match) | ✅ | ✅ Free from API | Zero |
| 1c | File size filter (±10%) | ✅ | ✅ Free from API | Zero |
| 2 | Text extraction + difflib/Jaccard (>90% match) | ✅ | ❌ Needs download | Low |
| 3 | Simhash fingerprint (distance < 3) | ✅ | ❌ Needs download | Low |
| 4 | Ollama embeddings + cosine similarity | ✅ | ❌ Needs download | High |

**Why Drive files can't use Levels 2-4:**
Drive API with `drive.readonly` returns metadata only — name, size, MD5, webViewLink.
Reading file content requires downloading the file, which is slow, uses bandwidth, and hits API quota.

### Default scan (fast, free, works on all sources)
Levels 1a + 1b + 1c run automatically on every scan:
```
Same MD5                      → exact duplicate (certain)
Similar name + same size      → very likely duplicate (flag for review)
Similar name + size ±10%      → possible duplicate (show to student)
```

### Deep scan (opt-in, local files only)
Student explicitly triggers — levels 2 + 3 run on local files:
- `pdfplumber` extracts text from PDFs
- `python-docx` extracts text from Word docs
- `difflib.SequenceMatcher` compares text — ratio > 0.90 = near duplicate
- `simhash` fingerprint for fast comparison at scale
- Catches: essay_v1.docx vs essay_v2.docx, PDF export of a Word doc

### Confidence score shown to student
Student never sees "Level 2" or "simhash" — just a confidence indicator:
```
bio_notes.pdf  ←→  Bio Notes Final.pdf
★★★★★ Exact copy (identical content)
★★★★☆ Very similar (95% match — probably same essay)
★★★☆☆ Similar (80% match — related content)
```

### Planned pipeline build order
1. Level 1a — done ✅
2. Level 1b + 1c — filename/size signals (small addition to detect_duplicates.py)
3. Level 2 — text extraction + difflib (needs pdfplumber + python-docx)
4. Level 3 — simhash (needs simhash library)
5. Level 4 — Ollama embeddings (already have Ollama, opt-in only)

### Performance: incremental MD5 computation (implemented 2026-04-13)
MD5 computation is incremental — local files are only read from disk when new or modified:

| File type | MD5 source | When recomputed |
|-----------|-----------|-----------------|
| Local (unchanged) | Stored in index | Never — `modified_at` unchanged |
| Local (new or modified) | Read from disk | When `modified_at` changes |
| Drive | Stored in index from API | Never — Drive API provides it free |

- `md5_computed_modified_at` stored alongside `md5` in the index
- Duplicate matching always runs in full (cheap dict lookups) — a new file can duplicate anything already in the index
- **Why:** Reading large local files (PDFs, videos) on every scan was wasteful; Drive MD5s were already free

---

## 10. Data Storage

**Current: JSON files in `~/.declutter/`**

| File | Contents |
|------|----------|
| `local_index.json` | Index of local files |
| `gdrive_<name>_index.json` | Index per connected Drive account |
| `local_expanded_map.json` | AI-learned keywords for local files |
| `gdrive_<name>_expanded_map.json` | AI-learned keywords per Drive account |
| `blacklist.json` | Folders excluded from scanning |
| `staging_log.json` | Soft-deleted local files |
| `credentials.json` | Google OAuth credentials for CLI (Desktop app type, never committed) |
| `credentials_web.json` | Google OAuth credentials for API (Web app type, never committed) |
| `drive_accounts/<name>.json` | Per-account OAuth tokens |

**Planned: SQLite migration (before cloud sync)**
- One `declutter.db` replaces all JSON files
- Easier to sync, faster queries on large indexes, no cross-file consistency issues
- `sqlite3` is built-in — no new dependencies
- Deferred until Drive integration is working end-to-end in JSON first

**Future option: SQLite on Google Drive for cross-device sync**
SQLite is a single file, so it can live anywhere — including the user's Google Drive folder:
```python
# paths.py — one-line change when ready
DATA_DIR = Path("~/Google Drive/My Drive/.declutter").expanduser()
```
- Google Drive desktop app syncs `declutter.db` automatically across Mac, Windows, Chromebook (Linux)
- Student's organised view follows them across all devices
- No server needed, no user database needed
- Safe for solo use (one device at a time) — Drive desktop handles sync gracefully for small files
- Risk: file corruption if two devices write simultaneously (unlikely for solo student use)

**Phase 1:** Local `~/.declutter/` (current — build this first)
**Phase 2 option:** Let user configure `DATA_DIR` via `settings.json` — they can point it to their Google Drive folder themselves. No code changes in the rest of the app.

---

## 11. Organised View

### Design decision: separate from generate_report (decided 2026-04-13)
`generate_report` stays lightweight — counts only, no file lists. This keeps it fast and suitable for the API layer.

A separate `generate_organised_view(index)` function will render files grouped by subject category:

```python
# tools/generate_organised_view.py (planned)
def generate_organised_view(index: dict) -> dict:
    """
    Returns files grouped by category, sorted by size descending within each group.
    Each file entry includes web_view_link so the UI can make them clickable.
    """
    # {
    #   "Biology": [
    #     { "name": "Bio Notes.pdf", "size_bytes": 204800, "source": "gdrive:school",
    #       "path": "gdrive:school/1aBcDeFgHiJk", "web_view_link": "https://...",
    #       "duplicate_of": null },
    #     ...
    #   ],
    #   "Math": [ ... ],
    # }
```

### Student-managed categories (planned for UI)
Students can customise their subject list:
- **Add a category** — e.g. "Drama", "Economics", "Latin" (not in default SEED_MAP)
- **Remove a category** — e.g. a student who doesn't take Music
- **Rename a category** — e.g. "pe" → "Physical Education"
- **Reassign a file** — drag a file from "other" to "Biology" manually

How it works under the hood:
- Custom categories stored in `settings.json` (planned) — adds to or overrides SEED_MAP
- Manual file reassignments stored as `category_override` in the index entry — never overwritten by the classifier
- `categorize_files` checks `category_override` first, before running the pipeline

### What the UI needs from this
- Each file shown as a clickable link:
  - Local files → "Show in Finder" / "Show in Explorer"
  - Drive files → `web_view_link` opens in browser
- Duplicate badge shown inline (e.g. ⚠️ Duplicate)
- Source badge per file (local / school / personal)
- Sorted: subjects alphabetically, files by size descending within subject
- "other" category shown last

### CLI version (interim)
Until the UI is built, the CLI renders this as a Rich table via `declutter report --organised` (planned).

---

## 12. UI Design

**Two-panel layout — one panel per source:**

```
┌──────────────┬──────────────┬──────────────────┐
│  My Computer │ School Drive │  Personal Drive  │
│              │              │                  │
│ Biology  12  │ Biology   8  │  Biology      3  │
│ Math      7  │ Math      5  │  English      6  │
│ English   3  │ English   9  │                  │
│              │              │                  │
│ Dupes: 4     │ Dupes: 4     │  Dupes: 1        │
└──────────────┴──────────────┴──────────────────┘
      Cross-source duplicates: 6 files found
```

- Panels are dynamic — one per connected Drive account, not hardcoded
- Panels are read-only by default — student sees, then decides
- Action row at bottom only appears when cross-source duplicates exist
- Built with `st.columns()` in Streamlit — son can own this module

**Build order:** Streamlit first (fastest) → PyQt6 or Tauri later for polished desktop app. Business logic in `tools/` and `core/` stays unchanged regardless of UI framework.

---

## 12. Gmail Integration (Tier 3)

Gmail integration is intentionally deferred to Tier 3 — not a cleanup tool, but an AI reasoning layer.

### What Gmail adds in Tier 3 (not cleanup)
- "What's due this week?" → scans Gmail + Google Calendar for deadlines
- "What did my teacher say about the history project?" → searches email threads by subject
- "Summarise all feedback I've received this semester" → reads assignment return emails
- Connects email context to Drive files — "the file my teacher mentioned in this email"

### Why not Tier 1/2
- Students don't feel email storage pain — school Gmail limits are generous
- Large attachment cleanup has low value for a 15-year-old
- Gmail's real value is **reasoning**, not **cleanup** — that needs the AI layer

### APIs needed
- `gmail.readonly` — read email threads and metadata
- Google Calendar API — deadlines, reminders, assignment due dates
- Claude API — reason across threads, summarise, extract deadlines

### Architecture (Tier 3)
```python
# connectors/gmail.py — implements SourceConnector
class GmailConnector(SourceConnector):
    source_id = "gmail:school"
    def scan() -> list[FileMetadata]  # email threads as structured data
```
- Same OAuth pattern as Drive: `declutter gmail-login school`
- Token stored at `~/.declutter/gmail_accounts/school.json`
- Email threads indexed alongside files — same unified index
- Claude API reasons across Gmail + Drive + local files together

---

## 13. Product Tiers

The product naturally grows into three tiers. Each tier is a complete product — not a feature gate.

---

### Tier 1 — Digital Declutter (Current)
**Target:** High school students, parents, schools
**Value:** Organised files, duplicate detection, space savings

| Feature | Status |
|---------|--------|
| Subject classification (5-step pipeline) | ✅ Built |
| Local file scanning + indexing | ✅ Built |
| MD5 duplicate detection | ✅ Built |
| Staging / safe delete (local) | ✅ Built |
| Google Drive scan (readonly) | ✅ Built |
| Incremental categorisation + MD5 | ✅ Built |
| Organised view CLI (report --organised) | ✅ Built |
| FastAPI layer | Planned |
| Streamlit UI | Planned |
| SQLite migration | Planned |

**Business model:** Free for students, paid for school IT deployment (storage savings = ROI)

---

### Tier 2 — AI Study Assistant (Premium Subscription)
**Target:** Students serious about academic performance, parents who want their kids to do well
**Value:** AI that knows your entire school life, helps you study, and keeps you on top of deadlines

Two tiers, clean story:
- **Tier 1 (free/school IT):** organise, deduplicate, clean up — Drive + local
- **Tier 2 (subscription):** AI study assistant — organise + understand + help me learn

| Feature | What it does |
|---------|-------------|
| **Near-duplicate detection** | Catches essay_v1 vs essay_v2, PDF export of a Word doc |
| **Image classification** | Photos of whiteboards, screenshots of slides → correct subject via LLaVA |
| **Video classification** | Frame extraction + AI → "Science Project.mp4" → correct subject |
| **Semantic search** | "Show my biology notes from last month" — finds by meaning not filename |
| **File summarisation** | Any PDF or doc summarised on demand via Claude API |
| **Subject tutor** | Quizzes student from their own notes — "test me on chapter 3" |
| **Gmail integration** | School communication, teacher feedback, assignment returns |
| **Google Calendar** | Due dates and reminders connected to files and subjects |
| **Memory graph** | Connections between files, emails, topics, deadlines, people |
| **Multi-step agent** | "Prepare me for tomorrow's exam" → finds notes + summarises + creates quiz |
| **Timeline builder** | "Show everything related to my history essay" chronologically |
| **Chat interface** | Natural language across all features — Ronit owns this module |

**Architecture requirements:**
- SQLite → vector database (pgvector or ChromaDB) for embeddings
- Background embedding pipeline — files embedded as they are indexed
- Memory graph (nodes = files/emails/deadlines, edges = relationships)
- Claude API for reasoning and summarisation
- Ollama for local embedding generation (free, offline)
- Multi-step agent via Claude Agent SDK
- Gmail API + Google Calendar API

### Two views in Tier 2

**Student view:**
- Files organised by subject across local + Drive
- Duplicates flagged, space savings shown
- "Help me study" — summarise notes, quiz me, semantic search
- "What's due this week?" — deadlines from Gmail + Google Calendar
- Chat interface for all of the above

**Teacher view:**
- All student submissions organised by assignment
- Spot missing submissions at a glance
- Flag duplicate submissions — academic integrity check
- "Summarise feedback I've given this semester"
- Assignment timeline — who submitted what and when

**Teacher AI assistant (from their own content):**
- "Generate a quiz from my chapter 3 notes" → pulls teacher's own Drive files
- "Summarise last year's exam papers" → finds and summarises past papers
- "Create an assignment brief based on my lesson plan" → drafts from existing content
- "What topics haven't I covered yet this term?" → reasons across lesson plans + calendar
- Years of accumulated content (past papers, rubrics, lesson plans) finally becomes searchable and useful

**Why the teacher view matters for sales:**
- Schools buy tools that help teachers, not just students
- Academic integrity (duplicate detection) is a real pain point for schools
- Teacher view turns Claire from a student tool into an institutional product
- One school licence covers all students + all teachers → higher contract value

**Why students and parents pay for this:**
- Saves hours of study prep — AI does the organising, student does the learning
- The value compounds — the longer they use it, the smarter it gets about their subjects
- No other tool connects Gmail + Drive + Calendar + local files into one study layer
- Parents see grades improve → retention is high

**Pricing model:** Monthly subscription — Claude API costs scale with usage

---

## 14. Chat Interface

Natural language wrapper around existing tools — the face of Tier 2:

- "What are my largest biology files?" → calls search + report
- "Show duplicates in my school Drive" → calls detect_duplicates filtered by source
- "Summarise my chemistry notes from this week" → file summarisation via Claude API
- "What did my teacher email me about the history project?" → Gmail + Drive reasoning
- "Test me on chapter 3 of my biology notes" → subject tutor
- "What's due this week?" → Google Calendar + Gmail deadlines

**Build path:**
- Tier 1: no chat needed — UI buttons are enough for organise/clean up
- Tier 2: full chat interface — Claude API routes natural language to the right tool

Good module for Ronit to own — conversational UI is UX work, business logic stays in tools/

---

## 15. Build Order

**Phase 1 — Tier 1 (current focus)**
1. ~~Subject classification pipeline~~ ✅
2. ~~Connector architecture + Google Drive connector~~ ✅
3. ~~Multi-source index (source, md5, webViewLink)~~ ✅
4. ~~CLI --source flag + drive-login/logout/accounts~~ ✅
5. ~~Progress bars for all pipeline steps~~ ✅
6. ~~Incremental categorisation + MD5 computation~~ ✅
7. ~~Organised view CLI (report --organised)~~ ✅
8. Test with real student Drive accounts
9. FastAPI layer
10. Streamlit UI (two-panel organised view)
11. SQLite migration

**Phase 2 — Tier 2 (AI Study Assistant)**
12. Near-duplicate detection (Levels 2-3)
13. Image classification via LLaVA (Ollama)
14. Video frame extraction + classification (ffmpeg)
15. Semantic search via embeddings
16. File summarisation via Claude API
17. Subject tutor / quiz mode
18. Gmail integration — school communication + teacher feedback
19. Google Calendar — deadlines connected to files and subjects
20. Vector database (ChromaDB or pgvector)
21. Memory graph (files + emails + deadlines)
22. Multi-step agent workflows (Claude Agent SDK)
23. Timeline builder
24. Chat interface (Ronit owns this)
25. Subscription billing
