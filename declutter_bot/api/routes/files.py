from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from declutter_bot.core.index_manager import load_index, save_index

router = APIRouter(prefix="/files", tags=["files"])


class CategoryUpdate(BaseModel):
    category: str
    source: str = "local"


@router.patch("/{path:path}/category")
def set_category(path: str, body: CategoryUpdate):
    """
    Update a file's category and mark it as manually_set=True.
    The pipeline will never overwrite this on future rescans.
    """
    index = load_index(body.source)
    if path not in index:
        raise HTTPException(status_code=404, detail=f"File not found in index: {path}")

    index[path] = {
        **index[path],
        "category": body.category,
        "manually_set": True,
    }
    save_index(index, body.source)
    return {"path": path, "category": body.category, "manually_set": True}
