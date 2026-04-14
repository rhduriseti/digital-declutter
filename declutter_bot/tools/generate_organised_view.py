from pathlib import Path


def generate_organised_view(index: dict) -> dict[str, list[dict]]:
    """
    Returns files grouped by subject category, sorted by size descending within each group.
    Each file entry includes web_view_link so the UI can make them clickable.

    Output shape:
    {
        "Biology": [
            { "name": "Bio Notes.pdf", "size_bytes": 204800, "source": "gdrive:school",
              "path": "gdrive:school/1aBcDeFgHiJk", "web_view_link": "https://...",
              "duplicate_of": None },
            ...
        ],
        "Math": [ ... ],
        "other": [ ... ],   # always last
    }
    """
    grouped: dict[str, list[dict]] = {}

    for path, entry in index.items():
        cat = entry.get("category") or "other"
        grouped.setdefault(cat, []).append({
            "name": entry.get("name", Path(path).name),
            "path": path,
            "size_bytes": entry.get("size_bytes", 0),
            "source": entry.get("source", "local"),
            "web_view_link": entry.get("web_view_link"),
            "duplicate_of": entry.get("duplicate_of"),
        })

    # Sort files within each category by size descending
    for cat in grouped:
        grouped[cat].sort(key=lambda f: f["size_bytes"], reverse=True)

    # Return categories alphabetically, "other" always last
    sorted_cats = sorted(k for k in grouped if k != "other")
    if "other" in grouped:
        sorted_cats.append("other")

    return {cat: grouped[cat] for cat in sorted_cats}
