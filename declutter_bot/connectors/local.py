import os
from pathlib import Path

from declutter_bot.connectors.base import SourceConnector
from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.tools.scan_folder import scan_folder


class LocalConnector(SourceConnector):
    """
    Connector for local filesystem. Wraps the existing scan_folder tool.
    """

    def __init__(self, folder_path: str):
        self.folder_path = folder_path

    @property
    def source_id(self) -> str:
        return "local"

    def scan(self) -> list[FileMetadata]:
        return scan_folder(self.folder_path)

    def trash(self, file_id: str) -> bool:
        """
        For local files, 'trash' means move to ~/.declutter_staging/.
        Handled by staging_manager — not implemented directly here.
        """
        raise NotImplementedError("Local trash is handled by staging_manager")

    def untrash(self, file_id: str) -> bool:
        raise NotImplementedError("Local untrash is handled by staging_manager")

    def permanent_delete(self, file_id: str) -> bool:
        try:
            os.remove(file_id)
            return True
        except OSError:
            return False
