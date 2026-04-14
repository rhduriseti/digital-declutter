from pathlib import Path

from declutter_bot.connectors.base import SourceConnector
from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.paths import DRIVE_ACCOUNTS_DIR, GOOGLE_CREDENTIALS_PATH

# drive.readonly — non-sensitive scope, easier Google verification
# Full drive scope added later once verified, UI doesn't change
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

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

# Drive API fields to fetch per file — md5Checksum and webViewLink are free, no download needed
DRIVE_FILE_FIELDS = (
    "id, name, mimeType, size, md5Checksum, modifiedTime, parents, webViewLink"
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
    def login(cls, account_name: str) -> "GoogleDriveConnector":
        """
        Run the OAuth2 flow for a new account. Opens the browser for the student to log in.
        Reads app credentials from ~/.declutter/credentials.json (placed there by the developer).
        Saves the student's token to ~/.declutter/drive_accounts/<account_name>.json.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        if not GOOGLE_CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"App credentials not found at {GOOGLE_CREDENTIALS_PATH}.\n"
                "Ask your administrator to place credentials.json in ~/.declutter/."
            )

        DRIVE_ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)

        flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CREDENTIALS_PATH), SCOPES)
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
