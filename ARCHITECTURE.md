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

Five steps, run in order, stop at first match:

| Step | Method | File |
|------|--------|------|
| 1 | Folder name keywords | `subject_classifier.py` |
| 2 | Filename keywords | `subject_classifier.py` |
| 3 | Seed map (15 subjects, ~200 keywords) | `utils.py` + `subject_classifier.py` |
| 4 | Expanded map (AI-learned keywords) | `subject_classifier.py` |
| 5 | Ollama local AI fallback (gemma3:4b) | `subject_classifier.py` |

- Subject list in Ollama prompt is derived from `SEED_MAP.keys()` — stays in sync automatically
- When Ollama classifies with confidence ≥ 0.85, new keywords are saved to `expanded_map.json`
- `expanded_map.json` grows over time, reducing AI calls

### Planned: Multimodal classification (images + videos)
Current pipeline (steps 1-5) is text-only — classifies from filename and path only. Gemma/Ollama cannot read image or video content.

**Images:**
- Local option: `ollama pull llava` — free, runs offline on Mac, handles images natively
- Cloud option: Claude API (claude-sonnet-4-6) — most accurate, costs per call
- Approach: pass image file directly to model → "what school subject is this related to?"

**Videos:**
- Extract a few frames using `ffmpeg` (free, runs locally): `ffmpeg -i video.mp4 -vf fps=1/10 frame_%03d.jpg`
- Pass frames to LLaVA (local) or Gemini 1.5 Pro (best for video, Google API)
- Don't need to analyse full video — 3-5 frames enough to classify subject

**Build order:**
1. Add `"science"` as catch-all subject in SEED_MAP (immediate, covers "Science Project 2.mp4" type filenames)
2. LLaVA via Ollama for image classification (Phase 2 — already have Ollama)
3. Video frame extraction + classification (Phase 2 — needs `ffmpeg`)
4. Gemini 1.5 Pro for full video understanding (Phase 3 — paid API)

**Why:** High school students commonly have photos of whiteboards, screenshots of slides, and recorded lab videos — all currently fall back to `image` or `video` category instead of their subject.

### Performance: incremental categorisation (implemented 2026-04-13)
Files are only re-categorised when necessary:

| Condition | Action |
|-----------|--------|
| `category` set + `modified_at` unchanged | Skip — reuse existing category |
| `category` set + `modified_at` changed | Re-categorise — filename/folder may have changed |
| No `category` (new file) | Categorise and store result |
| Old index entry (no `categorised_modified_at`) | Treat as unchanged — backward compatible |

- `categorised_modified_at` stored alongside `category` in the index
- Progress bar shows only the count of files actually being categorised, not full index size
- **Why:** Subject classification runs up to 5 pipeline steps including a local AI call (Ollama) — skipping unchanged files makes rescans fast

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
| `index.json` | All scanned files across all sources |
| `blacklist.json` | Folders excluded from scanning |
| `staging_log.json` | Soft-deleted files (local + Drive) |
| `expanded_map.json` | AI-learned keyword → subject mappings |
| `credentials.json` | Google app credentials (never committed) |
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

## 12. Gmail Integration (Planned)

Gmail is the natural next source after Drive — students receive assignments, feedback, and resources via email.

### What Gmail integration adds
- Large attachments (>5MB) — identified without downloading
- Duplicate attachments across emails — same file sent multiple times
- Old newsletters and bulk mail flagged for cleanup
- Attachments pulled into the unified index for cross-source deduplication

### Gmail API scope
- `gmail.readonly` — non-sensitive, same verification path as `drive.readonly`
- Metadata-only scan: sender, subject, date, attachment name + size
- Content/body never read — privacy by design

### How it fits the connector architecture
```python
# connectors/gmail.py — implements SourceConnector
class GmailConnector(SourceConnector):
    source_id = "gmail:school"  # or "gmail:personal"
    def scan() -> list[FileMetadata]  # attachments as FileMetadata
```

- Same `drive-login`-style auth: `declutter gmail-login school`
- Token stored at `~/.declutter/gmail_accounts/school.json`
- Attachments appear in the unified index with `source: "gmail:school"`
- Subject classifier runs on attachment filenames — same pipeline

### What shows in the UI
```
┌──────────────┬──────────────┬──────────────────┐
│  My Computer │ School Drive │  School Gmail    │
│              │              │                  │
│ Biology  12  │ Biology   8  │  Biology      4  │  ← email attachments
│ Math      7  │ Math      5  │  Math         2  │
└──────────────┴──────────────┴──────────────────┘
```

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
| Unified organised view (app-only) | Planned |
| Gmail attachments scan | Planned |
| FastAPI layer | Planned |
| Streamlit UI | Planned |
| SQLite migration | Planned |

**Business model:** Free for students, paid for school IT deployment (storage savings = ROI)

---

### Tier 2 — Smart File Assistant
**Target:** Students who want more than organisation
**Value:** Finds things, summarises things, spots patterns

| Feature | Notes |
|---------|-------|
| Near-duplicate detection (Level 2-3) | Text extraction + simhash |
| Semantic search | "Show my biology notes from last month" |
| File summarisation | "Summarise this PDF" via local Ollama |
| Subject tutor | Quiz student from their own notes |
| Cross-source search | One search across local + Drive + Gmail |

**LLM role:** Local Ollama (already integrated) handles summarisation and search. Claude API for higher quality when online.

---

### Tier 3 — Personal Digital Brain (Premium)
**Target:** Power users, students serious about academic performance
**Value:** AI that knows your entire digital life and reasons across it

This is where the LLM becomes essential — not optional:

| Feature | What it does |
|---------|-------------|
| **Semantic search** | Find files by meaning, not just filename |
| **Embeddings** | Every file vectorised — similarity search across thousands of docs |
| **Memory graph** | Connections between files, topics, people, dates |
| **Gmail + Drive reasoning** | "What did my teacher send me about the biology project?" spans email + Drive |
| **Multi-step agent workflows** | "Prepare me for tomorrow's exam" → finds notes + summarises + creates quiz |
| **Summarisation** | Any file or email thread summarised on demand |
| **Clustering** | Automatically groups related files across subjects and sources |
| **Timeline building** | "Show everything related to my history essay" in chronological order |

**Architecture requirements for Tier 3:**
- SQLite → vector database (pgvector or ChromaDB) for embedding storage
- Background embedding pipeline — files embedded as they are indexed
- Memory graph (nodes = files/people/topics, edges = relationships)
- Claude API for reasoning, Ollama for local embedding generation
- Multi-step agent via Claude Agent SDK

**Why this is the premium product:**
- Requires always-on API connection (Claude API cost)
- Embedding pipeline needs compute
- The value compounds over time — the longer a student uses it, the smarter it gets
- No other tool connects Gmail + Drive + local files into a single reasoning layer for students

**Pricing model:** Subscription — API costs are real and scale with usage

---

## 14. Chat Interface

Natural language wrapper around existing tools — entry point to Tier 2/3:

- "What are my largest biology files?" → calls search + report
- "Show duplicates in my school Drive" → calls detect_duplicates filtered by source
- "Summarise my chemistry notes from this week" → Tier 2 summarisation
- "What did my teacher email me about the history project?" → Tier 3 Gmail + Drive reasoning
- Long term: subject tutor that quizzes students from their own notes

**Build path:**
- Tier 1 chat: route natural language to CLI commands (Claude API, simple)
- Tier 2 chat: semantic search + summarisation responses
- Tier 3 chat: full agent with memory graph and multi-source reasoning

Good module for Ronit to own — conversational UI is UX work, business logic stays in tools/

---

## 15. Build Order

**Phase 1 — Tier 1 complete (current focus)**
1. ~~Subject classification pipeline~~ ✅
2. ~~Connector architecture + Google Drive connector~~ ✅
3. ~~Multi-source index (source, md5, webViewLink)~~ ✅
4. ~~CLI --source flag + drive-login/logout/accounts~~ ✅
5. ~~Progress bars for all pipeline steps~~ ✅
6. Test with real Drive credentials
7. FastAPI layer
8. Streamlit UI (two-panel organised view)
9. SQLite migration
10. Gmail integration

**Phase 2 — Tier 2**
11. Near-duplicate detection (Levels 2-3)
12. Semantic search
13. File summarisation via Ollama
14. Subject tutor / quiz mode
15. Tier 2 chat interface

**Phase 3 — Tier 3 (Premium)**
16. Vector database (ChromaDB or pgvector)
17. Background embedding pipeline
18. Memory graph
19. Gmail + Drive cross-source reasoning
20. Multi-step agent workflows (Claude Agent SDK)
21. Timeline builder
22. Tier 3 chat interface + subscription billing
