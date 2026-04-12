# Copilot Instructions for Digital Declutter

This project is a small CLI-driven Python tool that scans folders, indexes file metadata, categorizes files, detects duplicates, and generates reports.

Quick architecture
- CLI entry: `declutter_bot/cli/main.py` — parses commands and wires together the scan → index → categorize → dedupe → report pipeline (`run_pipeline`).
- Tools layer: `declutter_bot/tools/*` — each module is a single-step transformer or utility (e.g., `scan_folder`, `categorize_files`, `detect_duplicates`, `generate_report`). Use these as composable building blocks.
- Core: `declutter_bot/core/index_manager.py`, `file_metadata.py`, `utils.py` — persistence and index operations. `load_index()` / `save_index()` read/write the canonical index (stored in `data/index.json`).
- Data: `data/index.json` — canonical index persisted between runs. Treat it as authoritative for search/reporting.

Developer workflows (examples)
- Run full scan pipeline (from project root):
  - `python -m declutter_bot.cli.main scan /path/to/folder --pretty`
  - JSON output: add `--json`
- Generate global report:
  - `python -m declutter_bot.cli.main report`
- Run test suite: `pytest` (tests live in `tests/` and exercise the pipeline and index manager).

Project-specific patterns
- Functions return and accept the `index` structure (a dict mapping ids/paths to metadata). Most `tools/*` functions either accept an `index` and return a new/updated `index`, or return a `report` dict for rendering.
- Pipeline composition: `run_pipeline()` (in `cli/main.py`) shows the canonical order for operations — follow this ordering for new features that mutate the index.
- Reports: `generate_report_for_scan(index, folder_path)` produces a scan report shaped for immediate rendering; `generate_report(index)` produces a global report.
- CLI rendering: two presentation layers exist — rich-based pretty renderers (e.g., `render_scan_report`) and plain text fallbacks (e.g., `print_plain_scan_summary`). When adding new CLI output, support both `--pretty` and `--json` flags.

Integration points & extension guidance
- To add a new pipeline step:
  1. Add a new function under `declutter_bot/tools/` that accepts and returns an `index` (or returns a report when appropriate).
  2. Import and call it from `run_pipeline()` in `declutter_bot/cli/main.py` in the appropriate place.
  3. Update `save_index()`/`load_index()` usage only if persistence semantics change.
- Index migration: all code relies on `load_index()` to return the expected structure. If you change index shape, update `tests/*` and `generate_report*` helpers.

Tests and expectations
- Tests live in `tests/` and target behavior of the index manager, scan, categorization, duplicate detection, and reporting. New features must include focused unit tests under `tests/` following existing test patterns.

Files to consult when editing or extending
- `declutter_bot/cli/main.py` — CLI wiring, `run_pipeline()`, renderers.
- `declutter_bot/core/index_manager.py` — `load_index()`, `save_index()`, `update_index_with_scan()`.
- `declutter_bot/tools/scan_folder.py` — how files are discovered and basic metadata is built.
- `declutter_bot/tools/*.py` — existing tool implementations to copy conventions.
- `data/index.json` — sample persisted index; useful for manual testing.

Examples (concrete snippets)
- Pipeline order (canonical): `scan_folder` → `update_index_with_scan` → `load_index` → `categorize_files` → `detect_duplicates` → `save_index` → `generate_report_for_scan`.
- Renderers: support `--json` (dump the returned dict via `json.dumps`) and `--pretty` (call the rich renderer in `cli/main.py`).

When to ask for human help
- If a change requires altering the on-disk index shape (`data/index.json`) or changing the semantics of `load_index()`/`save_index()`, stop and request guidance — update tests and migration steps are required.

If anything is unclear or you'd like a different level of detail (examples of index shape, or mapped call sites), tell me which area to expand.
.