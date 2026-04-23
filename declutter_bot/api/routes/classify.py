from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from declutter_bot.core.index_manager import load_index, save_index
from declutter_bot.tools.categorize_files import categorize_files
from declutter_bot.api import scan_state

router = APIRouter(prefix="/classify", tags=["classify"])


class ClassifyRequest(BaseModel):
    source: str = "local"


def _run_classify(job_id: str, source: str):
    try:
        index = load_index(source)
        index = categorize_files(index)
        save_index(index, source)
        categorised = sum(1 for e in index.values() if e.get("category"))
        scan_state.set_done(job_id, {"source": source, "categorised": categorised})
    except Exception as e:
        scan_state.set_error(job_id, str(e))


@router.post("")
def start_classify(req: ClassifyRequest, background_tasks: BackgroundTasks):
    job_id = scan_state.create_job()
    background_tasks.add_task(_run_classify, job_id, req.source)
    return {"job_id": job_id, "status": "running"}


@router.get("/status/{job_id}")
def classify_status(job_id: str):
    from fastapi import HTTPException
    job = scan_state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job
