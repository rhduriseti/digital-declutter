from abc import ABC, abstractmethod
from declutter_bot.core.file_metadata import FileMetadata


class SourceConnector(ABC):
    """
    Base class for all file source integrations.
    Each connector (local, gdrive, gmail, dropbox) implements this interface
    so the core pipeline never needs to know which source it's working with.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """
        Unique identifier for this source, used as the 'source' field in the index.
        e.g. "local", "gdrive:school", "gdrive:personal"
        """
        ...

    @abstractmethod
    def scan(self) -> list[FileMetadata]:
        """Scan the source and return a list of FileMetadata objects."""
        ...

    @abstractmethod
    def trash(self, file_id: str) -> bool:
        """Move a file to trash (recoverable). Returns True on success."""
        ...

    @abstractmethod
    def untrash(self, file_id: str) -> bool:
        """Restore a file from trash. Returns True on success."""
        ...

    @abstractmethod
    def permanent_delete(self, file_id: str) -> bool:
        """Permanently delete a file. This cannot be undone. Returns True on success."""
        ...
