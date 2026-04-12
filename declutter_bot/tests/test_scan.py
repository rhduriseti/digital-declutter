import tempfile
from pathlib import Path

from declutter_bot.tools.scan_folder import scan_folder
from declutter_bot.core.file_metadata import FileMetadata


def test_scan_folder_basic():
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create some test files
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "image.jpg"

        file1.write_text("hello")
        file2.write_bytes(b"\x00\x01\x02")

        # Run the scanner
        results = scan_folder(tmp_path)

        # Assertions
        assert len(results) == 2
        assert all(isinstance(item, FileMetadata) for item in results)

        # Check names
        names = {item.name for item in results}
        assert "test1.txt" in names
        assert "image.jpg" in names


def test_scan_folder_ignores_directories():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create a subfolder
        subfolder = tmp_path / "sub"
        subfolder.mkdir()

        # Create a file inside it
        file_inside = subfolder / "inside.txt"
        file_inside.write_text("data")

        results = scan_folder(tmp_path)

        # Should only return the file, not the folder
        assert len(results) == 1
        assert results[0].name == "inside.txt"
