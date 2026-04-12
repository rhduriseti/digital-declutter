import tempfile
from pathlib import Path

from declutter_bot.tools.detect_duplicates import detect_duplicates, compute_md5


# ---------------------------------------------------------
# MD5 HASHING TESTS
# ---------------------------------------------------------

def test_compute_md5_same_content_same_hash():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        f1 = tmp / "a.txt"
        f2 = tmp / "b.txt"

        f1.write_text("hello world")
        f2.write_text("hello world")

        assert compute_md5(f1) == compute_md5(f2)


def test_compute_md5_different_content_different_hash():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        f1 = tmp / "a.txt"
        f2 = tmp / "b.txt"

        f1.write_text("hello")
        f2.write_text("world")

        assert compute_md5(f1) != compute_md5(f2)


# ---------------------------------------------------------
# DUPLICATE DETECTION TESTS
# ---------------------------------------------------------

def test_detect_duplicates_marks_duplicates():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create two identical files
        f1 = tmp / "a.txt"
        f2 = tmp / "b.txt"

        f1.write_text("same content")
        f2.write_text("same content")

        index = {
            str(f1): {
                "path": str(f1),
                "name": "a.txt",
                "extension": ".txt",
                "size_bytes": f1.stat().st_size,
                "created_at": None,
                "modified_at": None,
                "category": None,
                "duplicate_of": None,
            },
            str(f2): {
                "path": str(f2),
                "name": "b.txt",
                "extension": ".txt",
                "size_bytes": f2.stat().st_size,
                "created_at": None,
                "modified_at": None,
                "category": None,
                "duplicate_of": None,
            },
        }

        updated = detect_duplicates(index)

        # One should remain original, the other should point to it
        originals = [p for p, e in updated.items() if e["duplicate_of"] is None]
        duplicates = [p for p, e in updated.items() if e["duplicate_of"] is not None]

        assert len(originals) == 1
        assert len(duplicates) == 1

        dup_path = duplicates[0]
        assert updated[dup_path]["duplicate_of"] == originals[0]


def test_detect_duplicates_preserves_existing_duplicate_of():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        f1 = tmp / "a.txt"
        f2 = tmp / "b.txt"

        f1.write_text("same")
        f2.write_text("same")

        index = {
            str(f1): {
                "path": str(f1),
                "name": "a.txt",
                "extension": ".txt",
                "size_bytes": f1.stat().st_size,
                "created_at": None,
                "modified_at": None,
                "category": None,
                "duplicate_of": None,
            },
            str(f2): {
                "path": str(f2),
                "name": "b.txt",
                "extension": ".txt",
                "size_bytes": f2.stat().st_size,
                "created_at": None,
                "modified_at": None,
                "category": None,
                "duplicate_of": str(f1),  # already marked
            },
        }

        updated = detect_duplicates(index)

        # Should not overwrite existing duplicate_of
        assert updated[str(f2)]["duplicate_of"] == str(f1)


def test_detect_duplicates_ignores_missing_files():
    # If a file no longer exists, skip it
    index = {
        "/tmp/does_not_exist.txt": {
            "path": "/tmp/does_not_exist.txt",
            "name": "does_not_exist.txt",
            "extension": ".txt",
            "size_bytes": 0,
            "created_at": None,
            "modified_at": None,
            "category": None,
            "duplicate_of": None,
        }
    }

    updated = detect_duplicates(index)

    # Should remain unchanged
    assert updated["/tmp/does_not_exist.txt"]["duplicate_of"] is None
