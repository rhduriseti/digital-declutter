from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import warnings

from declutter_bot.tools.scan_folder import scan_folder
from declutter_bot.core.index_manager import update_index_with_scan, load_index, save_index
from declutter_bot.tools.categorize_files import categorize_files
from declutter_bot.tools.detect_duplicates import detect_duplicates
from declutter_bot.tools.generate_report import generate_report, generate_report_for_scan
from declutter_bot.connectors.gdrive import GoogleDriveConnector
from declutter_bot.api import scan_state

router = APIRouter(prefix="/scan", tags=["scan"])


class ScanRequest(BaseModel):
    folder: Optional[str] = None
    source: str = "local"


def _run_local_scan(job_id: str, folder: str):
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            scanned = scan_folder(folder)
            update_index_with_scan(scanned, "local")
            index = load_index("local")
            index = categorize_files(index)
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
            scanned = connector.scan()
            update_index_with_scan(scanned, source_id)
            index = load_index(source_id)
            index = categorize_files(index)
            index = detect_duplicates(index)
            save_index(index, source_id)
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
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job
