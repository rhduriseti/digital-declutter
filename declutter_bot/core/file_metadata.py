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
        )