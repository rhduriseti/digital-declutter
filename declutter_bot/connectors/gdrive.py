from pathlib import Path

from declutter_bot.connectors.base import SourceConnector
from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.paths import DRIVE_ACCOUNTS_DIR

# Google OAuth scopes needed — drive.file would be too narrow, we need full metadata read
SCOPES = ["https://www.googleapis.com/auth/drive"]

# File extensions we care about — mirrors scan_folder whitelist
DRIVE_EXT_WHITELIST = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx", ".txt", ".md",
    ".jpg", ".jpeg", ".png", ".heic",
    ".mp4", ".mov",
    ".py", ".ipynb", ".java", ".cpp", ".c",
    ".js", ".html", ".css",
}

# Google Workspace MIME types that export as real files
GOOGLE_MIME_EXPORT = {
    "application/vnd.google-apps.document": ".docx",
    "application/vnd.google-apps.spreadsheet": ".xlsx",
    "application/vnd.google-apps.presentation": ".pptx",
}

# Drive API fields to fetch per file — md5Checksum is free, no download needed
DRIVE_FILE_FIELDS = (
    "id, name, mimeType, size, md5Checksum, modifiedTime, parents"
)


class GoogleDriveConnector(SourceConnector):
    """
    Connector for Google Drive. One instance per connected account.

    account_name: the nickname given at login, e.g. "school" or "personal"
    Token is stored at ~/.declutter/drive_accounts/<account_name>.json
    """

    def __init__(self, account_name: str):
        self.account_name = account_name
        self._service = None  # lazy — only connect when needed

    @property
    def source_id(self) -> str:
        return f"gdrive:{self.account_name}"

    @property
    def token_path(self) -> Path:
        return DRIVE_ACCOUNTS_DIR / f"{self.account_name}.json"

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @classmethod
    def login(cls, account_name: str, credentials_file: str) -> "GoogleDriveConnector":
        """
        Run the OAuth2 flow for a new account. Opens the browser for the student to log in.
        Saves the token to ~/.declutter/drive_accounts/<account_name>.json.

        credentials_file: path to the credentials.json downloaded from Google Cloud Console.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        DRIVE_ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)

        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        creds = flow.run_local_server(port=0)

        connector = cls(account_name)
        connector._save_token(creds)
        return connector

    def _save_token(self, creds):
        DRIVE_ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as f:
            f.write(creds.to_json())

    def _load_creds(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        if not self.token_path.exists():
            raise FileNotFoundError(
                f"No token found for account '{self.account_name}'. "
                f"Run: declutter drive-login {self.account_name}"
            )

        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # Refresh token silently if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token(creds)

        return creds

    def _get_service(self):
        if self._service is None:
            from googleapiclient.discovery import build
            creds = self._load_creds()
            self._service = build("drive", "v3", credentials=creds)
        return self._service

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan(self) -> list[FileMetadata]:
        """
        List all files in Drive and return as FileMetadata objects.
        Uses pagination to handle large drives.
        md5Checksum is fetched for free — no file download needed.
        """
        service = self._get_service()
        results = []
        page_token = None

        while True:
            response = service.files().list(
                q="trashed=false",
                spaces="drive",
                fields=f"nextPageToken, files({DRIVE_FILE_FIELDS})",
                pageToken=page_token,
                pageSize=1000,
            ).execute()

            for f in response.get("files", []):
                metadata = self._to_file_metadata(f)
                if metadata:
                    results.append(metadata)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return results

    def _to_file_metadata(self, drive_file: dict) -> FileMetadata | None:
        """Convert a Drive API file dict to a FileMetadata object."""
        return FileMetadata.from_drive(
            drive_file,
            account_name=self.account_name,
            ext_whitelist=DRIVE_EXT_WHITELIST,
            google_mime_export=GOOGLE_MIME_EXPORT,
        )

    # ------------------------------------------------------------------
    # Trash / restore / delete
    # ------------------------------------------------------------------

    def _file_id_from(self, file_id: str) -> str:
        """
        Accept either a raw Drive file ID or the full path key used in the index
        e.g. "gdrive:school//1aBcDeFgHiJk" → "1aBcDeFgHiJk"
        """
        if "//" in file_id:
            return file_id.split("//")[-1]
        return file_id

    def trash(self, file_id: str) -> bool:
        try:
            self._get_service().files().update(
                fileId=self._file_id_from(file_id),
                body={"trashed": True}
            ).execute()
            return True
        except Exception:
            return False

    def untrash(self, file_id: str) -> bool:
        try:
            self._get_service().files().update(
                fileId=self._file_id_from(file_id),
                body={"trashed": False}
            ).execute()
            return True
        except Exception:
            return False

    def permanent_delete(self, file_id: str) -> bool:
        try:
            self._get_service().files().delete(
                fileId=self._file_id_from(file_id)
            ).execute()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Account management helpers
    # ------------------------------------------------------------------

    @staticmethod
    def list_accounts() -> list[str]:
        """Return names of all connected Drive accounts."""
        if not DRIVE_ACCOUNTS_DIR.exists():
            return []
        return [p.stem for p in DRIVE_ACCOUNTS_DIR.glob("*.json")]

    def logout(self):
        """Remove the saved token for this account."""
        if self.token_path.exists():
            self.token_path.unlink()
