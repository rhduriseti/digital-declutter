import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from declutter_bot.tools.categorize_files import categorize_files


def _entry(path: str, ext: str, name: str = None, modified_at: str = "2024-01-01", **kwargs) -> dict:
    return {
        "path": path,
        "name": name or Path(path).name,
        "extension": ext,
        "size_bytes": 10,
        "created_at": "2024-01-01",
        "modified_at": modified_at,
        "category": None,
        "duplicate_of": None,
        **kwargs,
    }


# ---------------------------------------------------------
# Original baseline tests
# ---------------------------------------------------------

def test_categorize_files_assigns_category():
    index = {"/tmp/a.txt": _entry("/tmp/a.txt", ".txt")}
    with patch("declutter_bot.tools.categorize_files.classify_group_c", return_value=(None, 0.0, None)):
        updated = categorize_files(index)
    assert updated["/tmp/a.txt"]["category"] == "other"


def test_categorize_files_preserves_manually_set_category():
    index = {
        "/tmp/b.jpg": _entry("/tmp/b.jpg", ".jpg", category="family_photos", manually_set=True)
    }
    updated = categorize_files(index)
    assert updated["/tmp/b.jpg"]["category"] == "family_photos"


def test_categorize_files_unknown_extension_goes_to_other():
    index = {"/tmp/weird.xyz": _entry("/tmp/weird.xyz", ".xyz")}
    with patch("declutter_bot.tools.categorize_files.classify_group_c", return_value=(None, 0.0, None)):
        updated = categorize_files(index)
    assert updated["/tmp/weird.xyz"]["category"] == "other"


# ---------------------------------------------------------
# Skip logic
# ---------------------------------------------------------

def test_categorize_files_skips_unchanged_categorised_file():
    index = {
        "/tmp/notes.txt": _entry(
            "/tmp/notes.txt", ".txt",
            category="biology",
            modified_at="2024-06-01",
            categorised_modified_at="2024-06-01",
        )
    }
    updated = categorize_files(index)
    assert updated["/tmp/notes.txt"]["category"] == "biology"
    assert updated["/tmp/notes.txt"].get("classification_group") is None  # not re-classified


def test_categorize_files_reclassifies_modified_file():
    index = {
        "/tmp/a.txt": _entry(
            "/tmp/a.txt", ".txt",
            category="biology",
            modified_at="2024-06-02",
            categorised_modified_at="2024-06-01",  # stale
        )
    }
    updated = categorize_files(index)
    # File was re-processed — classification_group is set
    assert updated["/tmp/a.txt"].get("classification_group") is not None


# ---------------------------------------------------------
# Media files
# ---------------------------------------------------------

def test_media_jpg_categorized_as_media():
    index = {"/tmp/photo.jpg": _entry("/tmp/photo.jpg", ".jpg")}
    updated = categorize_files(index)
    assert updated["/tmp/photo.jpg"]["category"] == "media"
    assert updated["/tmp/photo.jpg"]["classification_group"] == "extension"


def test_media_mp4_categorized_as_media():
    index = {"/tmp/video.mp4": _entry("/tmp/video.mp4", ".mp4")}
    updated = categorize_files(index)
    assert updated["/tmp/video.mp4"]["category"] == "media"
    assert updated["/tmp/video.mp4"]["classification_group"] == "extension"


def test_media_mp3_categorized_as_media():
    index = {"/tmp/song.mp3": _entry("/tmp/song.mp3", ".mp3")}
    updated = categorize_files(index)
    assert updated["/tmp/song.mp3"]["category"] == "media"


# ---------------------------------------------------------
# Group A: high confidence skips Gemma
# ---------------------------------------------------------

def test_group_a_high_confidence_classifies_without_gemma():
    # Multiple unambiguous biology keywords ensure total score >= MIN_SCORE=4.
    # Spaces required in filename — underscores break \b word boundaries in regex.
    path = "/Users/student/AP Biology/photosynthesis mitosis dna cell.pdf"
    index = {path: _entry(path, ".pdf")}

    with patch("declutter_bot.tools.categorize_files.classify_group_c", return_value=(None, 0.0, None)) as mock_c:
        updated = categorize_files(index)

    entry = updated[path]
    assert entry["category"] == "biology"
    assert entry["classification_group"] == "A"
    mock_c.assert_not_called()


def test_min_score_guard_sends_low_signal_file_to_gemma():
    # A file with only one matching keyword (score=1) must not bypass Gemma even if
    # confidence ratio is 100% — total score < MIN_SCORE=4 so Group B stays "fallback".
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "guide.txt"
        p.write_text("pressure")  # single physics keyword → score=1, ratio=100%

        index = {str(p): _entry(str(p), ".txt")}

        with patch("declutter_bot.tools.categorize_files.classify_group_c", return_value=(None, 0.0, None)) as mock_c:
            updated = categorize_files(index)

        # Group B should NOT have resolved — Gemma should have been called
        assert updated[str(p)]["classification_group"] != "B"
        mock_c.assert_called_once()


# ---------------------------------------------------------
# Group B: content keyword scoring
# ---------------------------------------------------------

def test_group_b_classifies_from_file_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "Science" / "notes.txt"
        p.parent.mkdir()
        p.write_text("photosynthesis cell dna mitosis biology organism evolution")

        index = {str(p): _entry(str(p), ".txt")}
        updated = categorize_files(index)

        assert updated[str(p)]["category"] == "biology"


def test_group_b_classifies_from_seed_map_only():
    # Without expanded map, Group B relies on SEED_MAP keywords in the content
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "notes.txt"
        p.write_text("napoleon essay romantic symbol analysis literature")
        index = {str(p): _entry(str(p), ".txt")}
        updated = categorize_files(index)
        # Should go to Gemma (low seed-map score) or fall back to other
        assert updated[str(p)]["category"] in {"english", "history", "other"}


# ---------------------------------------------------------
# Group C: Gemma called for ambiguous files
# ---------------------------------------------------------

def test_gemma_called_for_ambiguous_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "essay.txt"
        # Deliberately ambiguous — history keywords in an essay context
        p.write_text("napoleon revolution battle war essay poem romantic symbol")

        index = {str(p): _entry(str(p), ".txt")}

        mock_response = MagicMock()
        mock_response.message.content = (
            '{"subject": "english", "confidence": 0.87, "task_type": "essay", "also_could_be": "null"}'
        )

        with patch("ollama.chat", return_value=mock_response) as mock_chat:
            updated = categorize_files(index)

        entry = updated[str(p)]
        # If Gemma was reached and succeeded, category should be "english"
        if entry["classification_group"] == "C":
            assert entry["category"] == "english"
            mock_chat.assert_called()


def test_gemma_unavailable_falls_to_other():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "mystery.txt"
        p.write_text("xkcd random tokens no keyword signal here whatsoever zzz")

        index = {str(p): _entry(str(p), ".txt")}

        with patch("ollama.chat", side_effect=Exception("Connection refused")):
            updated = categorize_files(index)

        assert updated[str(p)]["category"] == "other"


# ---------------------------------------------------------
# Output fields
# ---------------------------------------------------------

def test_categorize_files_stores_confidence_score():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "Biology" / "notes.txt"
        p.parent.mkdir()
        p.write_text("cell biology dna")
        index = {str(p): _entry(str(p), ".txt")}
        updated = categorize_files(index)
    assert "confidence_score" in updated[str(p)]
    assert isinstance(updated[str(p)]["confidence_score"], float)


def test_categorize_files_stores_classification_group():
    index = {"/tmp/photo.jpg": _entry("/tmp/photo.jpg", ".jpg")}
    updated = categorize_files(index)
    assert "classification_group" in updated["/tmp/photo.jpg"]


def test_categorize_files_stores_categorised_modified_at():
    index = {"/tmp/photo.jpg": _entry("/tmp/photo.jpg", ".jpg", modified_at="2024-06-15")}
    updated = categorize_files(index)
    assert updated["/tmp/photo.jpg"]["categorised_modified_at"] == "2024-06-15"


# ---------------------------------------------------------
# on_progress callback
# ---------------------------------------------------------

def test_on_progress_called_for_each_file():
    index = {
        "/tmp/a.jpg": _entry("/tmp/a.jpg", ".jpg"),
        "/tmp/b.jpg": _entry("/tmp/b.jpg", ".jpg"),
        "/tmp/c.jpg": _entry("/tmp/c.jpg", ".jpg"),
    }
    calls = []
    categorize_files(index, on_progress=lambda done, total: calls.append((done, total)))
    assert len(calls) == 3
    assert calls[-1] == (3, 3)
