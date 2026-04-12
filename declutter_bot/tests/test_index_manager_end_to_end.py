import json
from pathlib import Path

from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.index_manager import update_index_with_scan


def test_update_index_with_scan(tmp_path, monkeypatch):
    # Redirect index.json to a temp folder
    monkeypatch.setattr("declutter_bot.core.index_manager.INDEX_PATH", tmp_path / "index.json")

    # Create a fake file metadata object
    f = FileMetadata(
        path=Path("/tmp/a.txt"),
        name="a.txt",
        extension=".txt",
        size_bytes=5,
        created_at=None,
        modified_at=None,
    )

    # Run the full update flow
    update_index_with_scan([f])

    # Load and verify — files is a dict keyed by path
    with open(tmp_path / "index.json") as fp:
        data = json.load(fp)

    assert len(data["files"]) == 1
    assert data["files"]["/tmp/a.txt"]["name"] == "a.txt"
