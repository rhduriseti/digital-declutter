from pathlib import Path
from declutter_bot.tools.generate_report import generate_report_for_scan

def test_generate_report_for_scan_filters_correctly(tmp_path):
    # Create fake folder structure
    folder = tmp_path / "docs"
    folder.mkdir()

    other = tmp_path / "other"
    other.mkdir()

    # Fake index entries
    index = {
        str(folder / "a.txt"): {"size_bytes": 10, "category": "text"},
        str(folder / "b.txt"): {"size_bytes": 20, "category": "text"},
        str(other / "c.txt"): {"size_bytes": 30, "category": "other"},
    }

    report = generate_report_for_scan(index, folder)

    assert report["total_files"] == 2
    assert report["total_size_bytes"] == 30
    assert report["categories"] == {"text": 2}
