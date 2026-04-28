import uuid

# job_id -> {status, result, error, progress}
_jobs: dict[str, dict] = {}


def create_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "result": None, "error": None, "progress": None}
    return job_id


def set_progress(job_id: str, files_scanned: int, total: int, current_file: str):
    if job_id in _jobs:
        _jobs[job_id]["progress"] = {
            "files_scanned": files_scanned,
            "total": total,
            "percent": int(files_scanned / total * 100) if total > 0 else 0,
            "current_file": current_file,
        }


def set_done(job_id: str, result: dict, warnings: list[str] = None):
    _jobs[job_id] = {"status": "done", "result": result, "warnings": warnings or [], "error": None, "progress": None}


def set_error(job_id: str, error: str):
    _jobs[job_id] = {"status": "error", "result": None, "error": error, "progress": None}


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)
