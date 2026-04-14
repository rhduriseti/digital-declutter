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

