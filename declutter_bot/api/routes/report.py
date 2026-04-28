from fastapi import APIRouter
from pathlib import Path
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


@router.get("/duplicates")
def get_duplicates(source: Optional[str] = None):
    index = load_combined_index()
    if source:
        index = {k: v for k, v in index.items() if v.get("source") == source}

    # Build a map from original path -> list of all copies (original + duplicates)
    groups: dict[str, list] = {}
    for path, entry in index.items():
        original = entry.get("duplicate_of") or path
        groups.setdefault(original, [])
        if entry.get("duplicate_of"):
            groups[original].append({"path": path, **entry})

    # Add the original file itself into each group
    for original_path, dupes in groups.items():
        if original_path in index:
            dupes.insert(0, {"path": original_path, **index[original_path]})

    result = []
    for original_path, copies in groups.items():
        if len(copies) < 2:
            continue
        size_bytes = copies[0].get("size_bytes", 0)
        space_wasted = size_bytes * (len(copies) - 1)
        result.append({
            "name": copies[0].get("name") or Path(original_path).name,
            "copies": len(copies),
            "size_bytes": size_bytes,
            "space_wasted_bytes": space_wasted,
            "files": [
                {
                    "path": c["path"],
                    "name": c.get("name") or Path(c["path"]).name,
                    "source": c.get("source", "local"),
                    "modified_at": c.get("modified_at"),
                    "web_view_link": c.get("web_view_link"),
                    "size_bytes": c.get("size_bytes", 0),
                }
                for c in copies
            ],
        })

    result.sort(key=lambda g: g["space_wasted_bytes"], reverse=True)
    return result
