from fastapi import APIRouter, Query

from declutter_bot.core.index_manager import load_combined_index
from declutter_bot.tools.search_index import search_index

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(q: str = Query(..., description="Search query")):
    index = load_combined_index()
    return search_index(index, q)
