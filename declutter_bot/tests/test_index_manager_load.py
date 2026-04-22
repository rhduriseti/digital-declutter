import json
from pathlib import Path

from declutter_bot.core.index_manager import load_index, save_index


def test_index_load_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("declutter_bot.core.paths.DATA_DIR", tmp_path)

    index = load_index("local")
    assert index == {}


def test_index_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr("declutter_bot.core.paths.DATA_DIR", tmp_path)

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

    save_index(sample, "local")
    loaded = load_index("local")

    assert loaded == sample
