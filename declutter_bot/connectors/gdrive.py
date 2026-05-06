from pathlib import Path

from declutter_bot.connectors.base import SourceConnector
from declutter_bot.core.file_metadata import FileMetadata
from declutter_bot.core.paths import DRIVE_ACCOUNTS_DIR, GOOGLE_CREDENTIALS_PATH, GOOGLE_WEB_CREDENTIALS_PATH

# drive.readonly — non-sensitive scope, easier Google verification
# drive.appdata — hidden per-app storage for saving index to user's own Drive
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.appdata",
]

APPDATA_INDEX_FILENAME = "claire_index.json"
APPDATA_TOKEN_FILENAME = "claire_token.json"

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
    def build_auth_url(cls, redirect_uri: str, state: str) -> str:
        """
        Build the Google OAuth2 authorization URL for the web flow.
        The caller must open this URL in the browser.
        """
        from google_auth_oauthlib.flow import Flow

        if not GOOGLE_WEB_CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Web credentials not found at {GOOGLE_WEB_CREDENTIALS_PATH}.\n"
                "Place credentials_web.json (Web application type) in ~/.declutter/."
            )

        flow = Flow.from_client_secrets_file(
            str(GOOGLE_WEB_CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        # Disable PKCE — requests-oauthlib 2.0 adds it automatically but
        # Google rejects it unless the client is explicitly configured for PKCE
        flow.oauth2session._client.code_challenge_method = None
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            state=state,
            prompt="consent",
            code_challenge=None,
            code_challenge_method=None,
        )
        return auth_url

    @classmethod
    def exchange_code(cls, account_name: str, code: str, redirect_uri: str) -> "GoogleDriveConnector":
        """
        Exchange an OAuth2 authorization code for a token and save it.
        Called by the API callback endpoint after Google redirects back.
        """
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_secrets_file(
            str(GOOGLE_WEB_CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        connector = cls(account_name)
        connector._save_token(flow.credentials)
        return connector

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
            import httplib2
            from googleapiclient.discovery import build
            from google_auth_httplib2 import AuthorizedHttp
            creds = self._load_creds()
            http = httplib2.Http(timeout=30)
            authorized_http = AuthorizedHttp(creds, http=http)
            self._service = build("drive", "v3", http=authorized_http)
        return self._service

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan(self, on_progress=None) -> list[FileMetadata]:
        """
        List all files in Drive and return as FileMetadata objects.
        Uses pagination to handle large drives.
        md5Checksum is fetched for free — no file download needed.
        on_progress(count) is called after each page with the running total found so far.
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

            if on_progress:
                on_progress(len(results))

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

    def get_file_text(self, file_id: str, mime_type: str | None, max_chars: int = 2000, ext: str = "") -> str:
        """
        Download the first max_chars of a Drive file as plain text into memory.
        Content is never written to disk and is discarded immediately after classification.

        PRIVACY NOTE: file content transiently passes through this process for
        classification only. It is never stored, logged, or sent to any third party.
        """
        service = self._get_service()

        # Google Workspace files (Docs, Slides) must be exported to plain text
        if mime_type and mime_type.startswith("application/vnd.google-apps"):
            try:
                data = service.files().export(
                    fileId=file_id, mimeType="text/plain"
                ).execute()
                text = data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else str(data)
                return text[:max_chars]
            except Exception:
                return ""

        # Regular files — download binary into memory buffer, parse by extension
        try:
            from googleapiclient.http import MediaIoBaseDownload
            from declutter_bot.tools.subject_classifier import extract_text_from_bytes
            import io
            if not ext and mime_type:
                ext_map = {
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
                    "application/pdf": ".pdf",
                }
                ext = ext_map.get(mime_type, "")
            request = service.files().get_media(fileId=file_id)
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
                if buf.tell() >= max_chars * 10:
                    break
            buf.seek(0)
            return extract_text_from_bytes(buf.read(), ext, max_chars)
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # appDataFolder — hidden per-app storage in the user's Drive
    # Index and token backups live here so data survives local disk wipes.
    # ------------------------------------------------------------------

    def read_appdata_file(self, filename: str) -> str | None:
        """Read a file from this Drive's appDataFolder. Returns content or None if not found."""
        service = self._get_service()
        try:
            results = service.files().list(
                spaces="appDataFolder",
                q=f"name='{filename}'",
                fields="files(id)",
                pageSize=1,
            ).execute()
            files = results.get("files", [])
            if not files:
                return None
            file_id = files[0]["id"]
            content = service.files().get_media(fileId=file_id).execute()
            return content.decode("utf-8") if isinstance(content, bytes) else content
        except Exception:
            return None

    def write_appdata_file(self, filename: str, content: str):
        """Write (or overwrite) a file in this Drive's appDataFolder."""
        from googleapiclient.http import MediaInMemoryUpload
        service = self._get_service()

        results = service.files().list(
            spaces="appDataFolder",
            q=f"name='{filename}'",
            fields="files(id)",
            pageSize=1,
        ).execute()
        existing = results.get("files", [])

        media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="application/json")

        if existing:
            service.files().update(
                fileId=existing[0]["id"],
                media_body=media,
            ).execute()
        else:
            service.files().create(
                body={"name": filename, "parents": ["appDataFolder"]},
                media_body=media,
            ).execute()

    def delete_appdata_file(self, filename: str):
        """Delete a file from this Drive's appDataFolder."""
        service = self._get_service()
        results = service.files().list(
            spaces="appDataFolder",
            q=f"name='{filename}'",
            fields="files(id)",
            pageSize=1,
        ).execute()
        for f in results.get("files", []):
            service.files().delete(fileId=f["id"]).execute()

    def trash_file(self, file_id: str):
        """Move a Drive file to trash (recoverable for 30 days)."""
        service = self._get_service()
        service.files().update(fileId=file_id, body={"trashed": True}).execute()

    def logout(self):
        """Revoke token with Google and remove locally. Index is kept so reconnecting restores without rescan."""
        if self.token_path.exists():
            try:
                creds = self._load_creds()
                import requests as req
                req.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": creds.token},
                    headers={"Content-type": "application/x-www-form-urlencoded"},
                    timeout=5,
                )
            except Exception:
                pass
            self.token_path.unlink()
