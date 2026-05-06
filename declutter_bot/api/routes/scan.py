import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import warnings

from declutter_bot.tools.scan_folder import scan_folder, count_files
from declutter_bot.core.index_manager import update_index_with_scan, load_index, save_index
from declutter_bot.tools.categorize_files import categorize_files
from declutter_bot.tools.detect_duplicates import detect_duplicates
from declutter_bot.tools.generate_report import generate_report, generate_report_for_scan
from declutter_bot.connectors.gdrive import GoogleDriveConnector, APPDATA_INDEX_FILENAME
from declutter_bot.core.paths import get_index_path
from declutter_bot.api import scan_state

router = APIRouter(prefix="/scan", tags=["scan"])


class ScanRequest(BaseModel):
    folder: Optional[str] = None
    source: str = "local"


def _run_local_scan(job_id: str, folder: str):
    try:
        total = count_files(folder)
        scan_state.set_progress(job_id, 0, total, "")

        def on_progress(current_file: str, files_scanned: int):
            scan_state.set_progress(job_id, files_scanned, total, current_file)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            scanned = scan_folder(folder, on_progress=on_progress)
            update_index_with_scan(scanned, "local")
            index = load_index("local")
            index = categorize_files(
                index,
                on_progress=lambda done, cat_total: scan_state.set_progress(job_id, done, cat_total, "Classifying files…"),
            )
            index = detect_duplicates(index)
            save_index(index, "local")
            report = generate_report_for_scan(index, Path(folder))
        scan_state.set_done(job_id, report, [str(w.message) for w in caught])
    except Exception as e:
        scan_state.set_error(job_id, str(e))


def _run_drive_scan(job_id: str, account_name: str):
    try:
        source_id = f"gdrive:{account_name}"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            connector = GoogleDriveConnector(account_name)

            # Restore existing index from appDataFolder before scanning so that
            # already-categorised files are preserved and only new/changed files get reclassified.
            if not get_index_path(source_id).exists():
                content = connector.read_appdata_file(APPDATA_INDEX_FILENAME)
                if content:
                    save_index(json.loads(content), source_id)

            scanned = connector.scan(
                on_progress=lambda count: scan_state.set_progress(job_id, count, 0, "Discovering files…")
            )
            update_index_with_scan(scanned, source_id)
            index = load_index(source_id)
            index = categorize_files(
                index,
                on_progress=lambda done, total: scan_state.set_progress(job_id, done, total, "Classifying files…"),
            )
            index = detect_duplicates(index)
            save_index(index, source_id)

            # Persist index to Drive appDataFolder — survives local disk wipes
            connector.write_appdata_file(APPDATA_INDEX_FILENAME, json.dumps(index, default=str))

            report = generate_report(index)
        scan_state.set_done(job_id, report, [str(w.message) for w in caught])
    except Exception as e:
        scan_state.set_error(job_id, str(e))


@router.post("")
def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    job_id = scan_state.create_job()

    if req.source.startswith("gdrive:"):
        account_name = req.source.split(":", 1)[1]
        background_tasks.add_task(_run_drive_scan, job_id, account_name)
    else:
        if not req.folder:
            raise HTTPException(status_code=400, detail="'folder' is required for local scan")
        background_tasks.add_task(_run_local_scan, job_id, req.folder)

    return {"job_id": job_id, "status": "running"}


@router.get("/status/{job_id}")
def scan_status(job_id: str):
    job = scan_state.get_job(job_id)
    if not job:
        # Return done instead of 404 — handles polling race after job cleanup
        return {"status": "done"}
    return job
