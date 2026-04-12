from declutter_bot.tools.search_index import search_index


def test_search_index_matches_name():
    index = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "category": "documents",
        },
        "/tmp/photo.jpg": {
            "path": "/tmp/photo.jpg",
            "name": "photo.jpg",
            "extension": ".jpg",
            "category": "images",
        },
    }

    results = search_index(index, "a.txt")

    assert len(results) == 1
    assert results[0]["name"] == "a.txt"


def test_search_index_matches_extension():
    index = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "category": "documents",
        },
        "/tmp/b.pdf": {
            "path": "/tmp/b.pdf",
            "name": "b.pdf",
            "extension": ".pdf",
            "category": "documents",
        },
    }

    results = search_index(index, "pdf")

    assert len(results) == 1
    assert results[0]["extension"] == ".pdf"


def test_search_index_matches_category():
    index = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "category": "documents",
        },
        "/tmp/photo.jpg": {
            "path": "/tmp/photo.jpg",
            "name": "photo.jpg",
            "extension": ".jpg",
            "category": "images",
        },
    }

    results = search_index(index, "images")

    assert len(results) == 1
    assert results[0]["category"] == "images"


def test_search_index_partial_match():
    index = {
        "/tmp/taxes_2023.pdf": {
            "path": "/tmp/taxes_2023.pdf",
            "name": "taxes_2023.pdf",
            "extension": ".pdf",
            "category": "documents",
        },
        "/tmp/notes.txt": {
            "path": "/tmp/notes.txt",
            "name": "notes.txt",
            "extension": ".txt",
            "category": "documents",
        },
    }

    results = search_index(index, "tax")

    assert len(results) == 1
    assert results[0]["name"] == "taxes_2023.pdf"


def test_search_index_no_matches():
    index = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "category": "documents",
        }
    }

    results = search_index(index, "xyz")

    assert results == []
