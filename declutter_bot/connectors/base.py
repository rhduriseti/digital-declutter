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
