import json
from pathlib import Path

from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.index_manager import update_index_with_scan


def test_update_index_with_scan(tmp_path, monkeypatch):
    monkeypatch.setattr("declutter_bot.core.paths.DATA_DIR", tmp_path)

    f = FileMetadata(
        path=Path("/tmp/a.txt"),
        name="a.txt",
        extension=".txt",
        size_bytes=5,
        created_at=None,
        modified_at=None,
    )

    update_index_with_scan([f], "local")

    with open(tmp_path / "local_index.json") as fp:
        data = json.load(fp)

    assert len(data["files"]) == 1
    assert data["files"]["/tmp/a.txt"]["name"] == "a.txt"
