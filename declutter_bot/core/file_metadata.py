from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

@dataclass
class FileMetadata:
    path: Path
    name: str
    extension: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    source: str = "local"
    md5: str | None = None
    category: str | None = None
    duplicate_of: str | None = None

    @classmethod
    def from_path(cls, file_path: Path):
        stat = file_path.stat()
        return cls(
            path=file_path,
            name=file_path.name,
            extension=file_path.suffix.lower(),
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            source="local",
        )

    @classmethod
    def from_drive(cls, drive_file: dict, account_name: str,
                   ext_whitelist: set, google_mime_export: dict):
        """
        Build a FileMetadata from a Google Drive API file dict.
        md5 is provided free by the Drive API — no download needed.
        Returns None if the file extension is not in the whitelist.
        """
        name = drive_file.get("name", "")
        mime = drive_file.get("mimeType", "")
        file_id = drive_file["id"]

        ext = google_mime_export.get(mime) or Path(name).suffix.lower()
        if ext not in ext_whitelist:
            return None

        modified = datetime.fromisoformat(
            drive_file.get("modifiedTime", "1970-01-01T00:00:00Z").replace("Z", "+00:00")
        )

        return cls(
            path=Path(f"gdrive:{account_name}//{file_id}"),
            name=name,
            extension=ext,
            size_bytes=int(drive_file.get("size", 0)),
            created_at=modified,
            modified_at=modified,
            source=f"gdrive:{account_name}",
            md5=drive_file.get("md5Checksum"),
        )