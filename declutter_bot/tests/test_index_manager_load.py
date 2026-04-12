import json
from pathlib import Path

from declutter_bot.core.index_manager import load_index, save_index


def test_index_load_empty(tmp_path, monkeypatch):
    # Redirect index.json to a temporary location
    monkeypatch.setattr("declutter_bot.core.index_manager.INDEX_PATH", tmp_path / "index.json")

    index = load_index()
    assert index == {}  # No file → empty index


def test_index_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr("declutter_bot.core.index_manager.INDEX_PATH", tmp_path / "index.json")

    sample = {
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

    save_index(sample)
    loaded = load_index()

    assert loaded == sample
