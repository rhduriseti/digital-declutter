from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from declutter_bot.core.staging_manager import (
    get_staging_summary,
    move_to_staging,
    restore_file,
    restore_all,
    empty_staging,
)

router = APIRouter(prefix="/staging", tags=["staging"])


class RestoreRequest(BaseModel):
    file: Optional[str] = None
    all: bool = False


class StageRequest(BaseModel):
    path: str
    source: Optional[str] = "local"


@router.get("")
def list_staged():
    return get_staging_summary()


@router.post("/stage")
def stage_file(req: StageRequest):
    if req.source and req.source.startswith("gdrive:"):
        account_name = req.source.split(":", 1)[1]
        file_id = req.path.split("/")[-1]
        from declutter_bot.connectors.gdrive import GoogleDriveConnector
        from declutter_bot.core.index_manager import load_index, save_index
        connector = GoogleDriveConnector(account_name)
        if not connector.token_path.exists():
            raise HTTPException(status_code=404, detail=f"No token for '{account_name}'")
        connector.trash_file(file_id)
        index = load_index(req.source)
        if req.path in index:
            del index[req.path]
            save_index(index, req.source)
        return {"staged": req.path, "source": req.source}
    else:
        staged_path = move_to_staging(req.path)
        return {"staged": req.path, "staging_path": staged_path}


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
