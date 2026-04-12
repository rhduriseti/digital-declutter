from pathlib import Path

from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.index_manager import merge_scans


def test_merge_scans_adds_new_files():
    existing = {}

    f = FileMetadata(
        path=Path("/tmp/a.txt"),
        name="a.txt",
        extension=".txt",
        size_bytes=5,
        created_at=None,
        modified_at=None,
    )

    merged = merge_scans(existing, [f])

    assert "/tmp/a.txt" in merged
    assert merged["/tmp/a.txt"]["name"] == "a.txt"


def test_merge_scans_preserves_category():
    existing = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "size_bytes": 5,
            "created_at": "2024-01-01T00:00:00",
            "modified_at": "2024-01-01T00:00:00",
            "category": "documents",
            "duplicate_of": None,
        }
    }

    # New scan with updated timestamp
    f = FileMetadata(
        path=Path("/tmp/a.txt"),
        name="a.txt",
        extension=".txt",
        size_bytes=5,
        created_at=None,
        modified_at="2024-02-01T00:00:00",
    )

    merged = merge_scans(existing, [f])

    assert merged["/tmp/a.txt"]["category"] == "documents"


def test_merge_scans_preserves_files_not_in_current_scan():
    # Files not in the current scan are intentionally kept in the index
    # (they may exist in other folders that weren't part of this scan)
    existing = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "size_bytes": 5,
            "created_at": "2024-01-01T00:00:00",
            "modified_at": "2024-01-01T00:00:00",
            "category": None,
            "duplicate_of": None,
        }
    }

    merged = merge_scans(existing, [])

    assert "/tmp/a.txt" in merged
