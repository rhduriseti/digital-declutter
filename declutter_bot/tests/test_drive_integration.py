"""
Tests for Google Drive integration.
Covers: FileMetadata.from_drive(), stored-md5 duplicate detection,
source field in index, Drive-aware staging (trash/restore/empty).
"""
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.index_manager import merge_scans, purge_source_from_index
from declutter_bot.tools.detect_duplicates import detect_duplicates
from declutter_bot.tools.delete_duplicates import get_deletable_paths


# ---------------------------------------------------------
# FileMetadata.from_drive()
# ---------------------------------------------------------

DRIVE_FILE = {
    "id": "1aBcDeFgHiJk",
    "name": "Bio Notes.pdf",
    "mimeType": "application/pdf",
    "size": "204800",
    "md5Checksum": "abc123",
    "modifiedTime": "2024-03-01T10:00:00Z",
    "parents": ["folder_id"],
}

EXT_WHITELIST = {".pdf", ".docx", ".txt"}
GOOGLE_MIME_EXPORT = {
    "application/vnd.google-apps.document": ".docx",
}


def test_from_drive_basic_fields():
    meta = FileMetadata.from_drive(DRIVE_FILE, "school", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta is not None
    assert meta.name == "Bio Notes.pdf"
    assert meta.extension == ".pdf"
    assert meta.size_bytes == 204800
    assert meta.md5 == "abc123"
    assert meta.source == "gdrive:school"
    assert str(meta.path) == "gdrive:school/1aBcDeFgHiJk"


def test_from_drive_source_uses_account_name():
    meta = FileMetadata.from_drive(DRIVE_FILE, "personal", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta.source == "gdrive:personal"
    assert "personal" in str(meta.path)


def test_from_drive_returns_none_for_non_whitelisted_extension():
    drive_file = {**DRIVE_FILE, "name": "archive.zip", "mimeType": "application/zip"}
    meta = FileMetadata.from_drive(drive_file, "school", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta is None


def test_from_drive_google_doc_gets_docx_extension():
    drive_file = {
        **DRIVE_FILE,
        "name": "My Essay",
        "mimeType": "application/vnd.google-apps.document",
        "md5Checksum": None,  # Google Docs don't have md5
    }
    meta = FileMetadata.from_drive(drive_file, "school", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta is not None
    assert meta.extension == ".docx"


def test_from_drive_missing_size_defaults_to_zero():
    drive_file = {**DRIVE_FILE}
    del drive_file["size"]
    meta = FileMetadata.from_drive(drive_file, "school", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta.size_bytes == 0


def test_from_drive_missing_md5_is_none():
    drive_file = {**DRIVE_FILE}
    del drive_file["md5Checksum"]
    meta = FileMetadata.from_drive(drive_file, "school", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta.md5 is None


# ---------------------------------------------------------
# detect_duplicates — stored md5 (Drive files)
# ---------------------------------------------------------

def test_detect_duplicates_uses_stored_md5_for_drive_files():
    """Drive files have md5 in the index — no disk read needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        local_file = Path(tmpdir) / "bio_notes.pdf"
        local_file.write_bytes(b"same content")

        index = {
            str(local_file): {
                "path": str(local_file),
                "name": "bio_notes.pdf",
                "extension": ".pdf",
                "size_bytes": 12,
                "created_at": None,
                "modified_at": None,
                "source": "local",
                "md5": None,
                "category": None,
                "duplicate_of": None,
            },
            "gdrive:school/1aBcDeFgHiJk": {
                "path": "gdrive:school/1aBcDeFgHiJk",
                "name": "bio_notes.pdf",
                "extension": ".pdf",
                "size_bytes": 12,
                "created_at": None,
                "modified_at": None,
                "source": "gdrive:school",
                "md5": "793953ee398d864ec40252df9554c3e6",  # md5 of b"same content"
                "category": None,
                "duplicate_of": None,
            },
        }

        updated = detect_duplicates(index)

        paths_with_duplicates = [p for p, e in updated.items() if e["duplicate_of"]]
        assert len(paths_with_duplicates) == 1


def test_detect_duplicates_skips_drive_file_with_no_md5_and_no_disk():
    """Drive file with no md5 and no local path should be skipped gracefully."""
    index = {
        "gdrive:school//missingmd5": {
            "path": "gdrive:school//missingmd5",
            "name": "unknown.pdf",
            "extension": ".pdf",
            "size_bytes": 0,
            "created_at": None,
            "modified_at": None,
            "source": "gdrive:school",
            "md5": None,
            "category": None,
            "duplicate_of": None,
        }
    }

    # Should not raise
    updated = detect_duplicates(index)
    assert updated["gdrive:school//missingmd5"]["duplicate_of"] is None


# ---------------------------------------------------------
# merge_scans — source and md5 fields
# ---------------------------------------------------------

def test_merge_scans_stores_source_for_local_file():
    meta = FileMetadata(
        path=Path("/tmp/a.pdf"),
        name="a.pdf",
        extension=".pdf",
        size_bytes=100,
        created_at=None,
        modified_at=None,
        source="local",
        md5=None,
    )
    merged = merge_scans({}, [meta])
    assert merged["/tmp/a.pdf"]["source"] == "local"


def test_merge_scans_stores_source_and_md5_for_drive_file():
    meta = FileMetadata(
        path=Path("gdrive:school/1aBcDeFgHiJk"),
        name="Bio Notes.pdf",
        extension=".pdf",
        size_bytes=204800,
        created_at=datetime(2024, 3, 1),
        modified_at=datetime(2024, 3, 1),
        source="gdrive:school",
        md5="abc123",
    )
    merged = merge_scans({}, [meta])
    entry = merged["gdrive:school/1aBcDeFgHiJk"]
    assert entry["source"] == "gdrive:school"
    assert entry["md5"] == "abc123"


# ---------------------------------------------------------
# get_deletable_paths — source field included
# ---------------------------------------------------------

def test_get_deletable_paths_includes_source_and_web_view_link():
    index = {
        "gdrive:school/1aBcDeFgHiJk": {
            "path": "gdrive:school/1aBcDeFgHiJk",
            "name": "bio_notes.pdf",
            "extension": ".pdf",
            "size_bytes": 1000,
            "source": "gdrive:school",
            "md5": "abc123",
            "web_view_link": "https://drive.google.com/file/d/1aBcDeFgHiJk/view",
            "category": None,
            "duplicate_of": "/local/bio_notes.pdf",
        }
    }
    targets = get_deletable_paths(index)
    assert len(targets) == 1
    assert targets[0]["source"] == "gdrive:school"
    assert targets[0]["web_view_link"] == "https://drive.google.com/file/d/1aBcDeFgHiJk/view"


def test_get_deletable_paths_local_source_defaults():
    """Entries without a source field should default to 'local'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "old.pdf"
        f.write_text("x")
        index = {
            str(f): {
                "path": str(f),
                "name": "old.pdf",
                "extension": ".pdf",
                "size_bytes": 1,
                "category": None,
                "duplicate_of": "/other/old.pdf",
                # no 'source' key — simulates old index entries
            }
        }
        targets = get_deletable_paths(index)
        assert targets[0]["source"] == "local"


# ---------------------------------------------------------
# delete_duplicates — Drive files are skipped, not deleted
# ---------------------------------------------------------

def test_delete_duplicates_skips_drive_files():
    """Drive duplicates should be skipped — student deletes manually via webViewLink."""
    from declutter_bot.tools.delete_duplicates import delete_duplicates

    index = {
        "gdrive:school/1aBcDeFgHiJk": {
            "path": "gdrive:school/1aBcDeFgHiJk",
            "name": "bio_notes.pdf",
            "size_bytes": 1000,
            "source": "gdrive:school",
            "duplicate_of": "/local/bio_notes.pdf",
        }
    }
    targets = [{"path": "gdrive:school/1aBcDeFgHiJk", "source": "gdrive:school", "size_bytes": 1000}]

    updated, deleted, skipped = delete_duplicates(index, targets)

    assert len(deleted) == 0
    assert "gdrive:school/1aBcDeFgHiJk" in skipped


# ---------------------------------------------------------
# webViewLink stored in FileMetadata and index
# ---------------------------------------------------------

def test_from_drive_stores_web_view_link():
    drive_file = {**DRIVE_FILE, "webViewLink": "https://drive.google.com/file/d/1aBcDeFgHiJk/view"}
    meta = FileMetadata.from_drive(drive_file, "school", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta.web_view_link == "https://drive.google.com/file/d/1aBcDeFgHiJk/view"


def test_from_drive_web_view_link_none_when_missing():
    drive_file = {**DRIVE_FILE}
    drive_file.pop("webViewLink", None)
    meta = FileMetadata.from_drive(drive_file, "school", EXT_WHITELIST, GOOGLE_MIME_EXPORT)
    assert meta.web_view_link is None


# ---------------------------------------------------------
# purge_source_from_index — logout cleans up index
# ---------------------------------------------------------

def test_purge_source_removes_source_index_file(tmp_path, monkeypatch):
    """purge_source_from_index deletes the per-source index file and returns entry count."""
    monkeypatch.setattr("declutter_bot.core.paths.DATA_DIR", tmp_path)

    from declutter_bot.core.index_manager import save_index

    personal_index = {
        "gdrive:personal/file1": {"source": "gdrive:personal", "name": "a.pdf"},
        "gdrive:personal/file2": {"source": "gdrive:personal", "name": "b.pdf"},
    }
    school_index = {
        "gdrive:school/file3": {"source": "gdrive:school", "name": "c.pdf"},
    }
    save_index(personal_index, "gdrive:personal")
    save_index(school_index, "gdrive:school")

    removed = purge_source_from_index("gdrive:personal")

    assert removed == 2
    assert not (tmp_path / "gdrive_personal_index.json").exists()
    assert (tmp_path / "gdrive_school_index.json").exists()


def test_purge_source_returns_zero_when_no_index_file(tmp_path, monkeypatch):
    """Returns 0 when the source has no index file."""
    monkeypatch.setattr("declutter_bot.core.paths.DATA_DIR", tmp_path)

    removed = purge_source_from_index("gdrive:personal")
    assert removed == 0


def test_purge_source_handles_empty_index(tmp_path, monkeypatch):
    """Returns 0 when the source index file exists but is empty."""
    monkeypatch.setattr("declutter_bot.core.paths.DATA_DIR", tmp_path)

    from declutter_bot.core.index_manager import save_index

    save_index({}, "gdrive:personal")

    removed = purge_source_from_index("gdrive:personal")
    assert removed == 0


def test_merge_scans_stores_web_view_link():
    meta = FileMetadata(
        path=Path("gdrive:school/1aBcDeFgHiJk"),
        name="Bio Notes.pdf",
        extension=".pdf",
        size_bytes=204800,
        created_at=datetime(2024, 3, 1),
        modified_at=datetime(2024, 3, 1),
        source="gdrive:school",
        md5="abc123",
        web_view_link="https://drive.google.com/file/d/1aBcDeFgHiJk/view",
    )
    merged = merge_scans({}, [meta])
    entry = merged["gdrive:school/1aBcDeFgHiJk"]
    assert entry["web_view_link"] == "https://drive.google.com/file/d/1aBcDeFgHiJk/view"
