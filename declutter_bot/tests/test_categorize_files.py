from declutter_bot.tools.categorize_files import categorize_files


def test_categorize_files_assigns_category():
    index = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "size_bytes": 5,
            "created_at": "2024-01-01",
            "modified_at": "2024-01-01",
            "category": None,
            "duplicate_of": None,
        }
    }

    updated = categorize_files(index)

    assert updated["/tmp/a.txt"]["category"] == "documents"


def test_categorize_files_preserves_existing_category():
    index = {
        "/tmp/b.jpg": {
            "path": "/tmp/b.jpg",
            "name": "b.jpg",
            "extension": ".jpg",
            "size_bytes": 10,
            "created_at": "2024-01-01",
            "modified_at": "2024-01-01",
            "category": "family_photos",
            "duplicate_of": None,
        }
    }

    updated = categorize_files(index)

    assert updated["/tmp/b.jpg"]["category"] == "family_photos"


def test_categorize_files_unknown_extension_goes_to_other():
    index = {
        "/tmp/weird.xyz": {
            "path": "/tmp/weird.xyz",
            "name": "weird.xyz",
            "extension": ".xyz",
            "size_bytes": 1,
            "created_at": "2024-01-01",
            "modified_at": "2024-01-01",
            "category": None,
            "duplicate_of": None,
        }
    }

    updated = categorize_files(index)

    assert updated["/tmp/weird.xyz"]["category"] == "other"
