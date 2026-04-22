from fastapi import APIRouter
from pydantic import BaseModel

from declutter_bot.core.index_manager import untrack_folder

router = APIRouter(prefix="/untrack", tags=["untrack"])


class UntrackRequest(BaseModel):
    folder: str


@router.post("")
def untrack(req: UntrackRequest):
    removed = untrack_folder(req.folder)
    return {"folder": req.folder, "removed": removed}
