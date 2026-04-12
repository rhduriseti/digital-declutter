from declutter_bot.tools.generate_report import generate_report


def test_generate_report_empty_index():
    report = generate_report({})

    assert report["total_files"] == 0
    assert report["total_size_bytes"] == 0
    assert report["categories"] == {}
    assert report["duplicates"] == []
    assert report["space_saved_by_deleting_duplicates_bytes"] == 0
    assert report["largest_files"] == []


def test_generate_report_basic_counts():
    index = {
        "/tmp/a.txt": {
            "path": "/tmp/a.txt",
            "name": "a.txt",
            "extension": ".txt",
            "size_bytes": 10,
            "category": "documents",
            "duplicate_of": None,
        },
        "/tmp/b.jpg": {
            "path": "/tmp/b.jpg",
            "name": "b.jpg",
            "extension": ".jpg",
            "size_bytes": 20,
            "category": "images",
            "duplicate_of": None,
        },
    }

    report = generate_report(index)

    assert report["total_files"] == 2
    assert report["total_size_bytes"] == 30
    assert report["categories"] == {"documents": 1, "images": 1}


def test_generate_report_duplicates():
    index = {
        "/tmp/original.jpg": {
            "path": "/tmp/original.jpg",
            "name": "original.jpg",
            "extension": ".jpg",
            "size_bytes": 100,
            "category": "images",
            "duplicate_of": None,
        },
        "/tmp/copy1.jpg": {
            "path": "/tmp/copy1.jpg",
            "name": "copy1.jpg",
            "extension": ".jpg",
            "size_bytes": 100,
            "category": "images",
            "duplicate_of": "/tmp/original.jpg",
        },
        "/tmp/copy2.jpg": {
            "path": "/tmp/copy2.jpg",
            "name": "copy2.jpg",
            "extension": ".jpg",
            "size_bytes": 100,
            "category": "images",
            "duplicate_of": "/tmp/original.jpg",
        },
    }

    report = generate_report(index)

    assert len(report["duplicates"]) == 2

    paths = {f["path"] for f in report["duplicates"]}
    assert paths == {"/tmp/copy1.jpg", "/tmp/copy2.jpg"}

    for f in report["duplicates"]:
        assert f["duplicate_of"] == "/tmp/original.jpg"
        assert f["size_bytes"] == 100
        assert f["category"] == "images"

    assert report["space_saved_by_deleting_duplicates_bytes"] == 200


def test_generate_report_largest_files_sorted():
    index = {
        "/tmp/small.txt": {
            "path": "/tmp/small.txt",
            "name": "small.txt",
            "extension": ".txt",
            "size_bytes": 5,
            "category": "documents",
            "duplicate_of": None,
        },
        "/tmp/medium.txt": {
            "path": "/tmp/medium.txt",
            "name": "medium.txt",
            "extension": ".txt",
            "size_bytes": 50,
            "category": "documents",
            "duplicate_of": None,
        },
        "/tmp/large.txt": {
            "path": "/tmp/large.txt",
            "name": "large.txt",
            "extension": ".txt",
            "size_bytes": 500,
            "category": "documents",
            "duplicate_of": None,
        },
    }

    report = generate_report(index)

    largest = report["largest_files"]

    assert largest[0]["path"] == "/tmp/large.txt"
    assert largest[1]["path"] == "/tmp/medium.txt"
    assert largest[2]["path"] == "/tmp/small.txt"
