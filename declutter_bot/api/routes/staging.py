from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from declutter_bot.core.staging_manager import (
    get_staging_summary,
    restore_file,
    restore_all,
    empty_staging,
)

router = APIRouter(prefix="/staging", tags=["staging"])


class RestoreRequest(BaseModel):
    file: Optional[str] = None
    all: bool = False


@router.get("")
def list_staged():
    return get_staging_summary()


@router.post("/restore")
def restore(req: RestoreRequest):
    if req.all:
        restored, failed = restore_all()
        return {"restored": restored, "failed": failed}
    if req.file:
        if restore_file(req.file):
            return {"restored": req.file}
        raise HTTPException(status_code=404, detail=f"Not found in staging: {req.file}")
    raise HTTPException(status_code=400, detail="Provide 'file' or set 'all' to true")


@router.delete("")
def empty():
    deleted, bytes_freed = empty_staging()
    return {"deleted": deleted, "bytes_freed": bytes_freed}
