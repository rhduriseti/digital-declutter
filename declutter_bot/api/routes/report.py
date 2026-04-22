from fastapi import APIRouter
from typing import Optional

from declutter_bot.core.index_manager import load_combined_index
from declutter_bot.tools.generate_report import generate_report
from declutter_bot.tools.generate_organised_view import generate_organised_view

router = APIRouter(prefix="/report", tags=["report"])


@router.get("")
def get_report(source: Optional[str] = None):
    index = load_combined_index()
    if source:
        index = {k: v for k, v in index.items() if v.get("source") == source}
    return generate_report(index)


@router.get("/organised")
def get_organised(source: Optional[str] = None):
    index = load_combined_index()
    if source:
        index = {k: v for k, v in index.items() if v.get("source") == source}
    return generate_organised_view(index)
