from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from declutter_bot.core.blacklist_manager import (
    load_blacklist,
    add_to_blacklist,
    remove_from_blacklist,
)

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


class FolderRequest(BaseModel):
    folder: str


@router.get("")
def list_blacklist():
    return {"folders": sorted(load_blacklist())}


@router.post("")
def add(req: FolderRequest):
    added, purged = add_to_blacklist(req.folder)
    if not added:
        raise HTTPException(status_code=409, detail=f"Already blacklisted: {req.folder}")
    return {"added": req.folder, "index_entries_removed": purged}


@router.delete("")
def remove(req: FolderRequest):
    if not remove_from_blacklist(req.folder):
        raise HTTPException(status_code=404, detail=f"Not found in blacklist: {req.folder}")
    return {"removed": req.folder}
