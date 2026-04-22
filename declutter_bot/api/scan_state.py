import uuid

# job_id -> {status: "running"|"done"|"error", result: dict|None, error: str|None}
_jobs: dict[str, dict] = {}


def create_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    return job_id


def set_done(job_id: str, result: dict, warnings: list[str] = None):
    _jobs[job_id] = {"status": "done", "result": result, "warnings": warnings or [], "error": None}


def set_error(job_id: str, error: str):
    _jobs[job_id] = {"status": "error", "result": None, "error": error}


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)
