import json
import secrets
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from declutter_bot.connectors.gdrive import GoogleDriveConnector, APPDATA_INDEX_FILENAME
from declutter_bot.core.index_manager import load_index, save_index
from declutter_bot.core.paths import get_index_path

router = APIRouter(prefix="/drive", tags=["drive"])

REDIRECT_URI = "http://localhost:8000/drive/login/callback"

# state -> account_name (in-memory, only lives for the duration of the OAuth flow)
_pending: dict[str, str] = {}


@router.get("/accounts")
def list_accounts():
    return {"accounts": GoogleDriveConnector.list_accounts()}


@router.get("/login/start/{account_name}")
def login_start(account_name: str):
    try:
        state = secrets.token_urlsafe(16)
        _pending[state] = account_name
        auth_url = GoogleDriveConnector.build_auth_url(REDIRECT_URI, state)
        return {"auth_url": auth_url, "account_name": account_name}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/login/callback")
def login_callback(code: str = None, state: str = None, error: str = None):
    if error:
        return HTMLResponse(f"""
            <html><body style="font-family:sans-serif;padding:2rem">
                <h2>&#10060; Google authorisation failed</h2>
                <p><b>Reason:</b> {error}</p>
                <p>Close this tab and try again. If this keeps happening, check that
                <code>http://localhost:8000/drive/login/callback</code> is listed as an
                authorised redirect URI in your Google Cloud Console.</p>
            </body></html>
        """)

    if not code or not state:
        return HTMLResponse("""
            <html><body style="font-family:sans-serif;padding:2rem">
                <h2>&#10060; Authorisation incomplete</h2>
                <p>No authorisation code was received from Google. Close this tab and try again.</p>
            </body></html>
        """)

    account_name = _pending.pop(state, None)
    if not account_name:
        return HTMLResponse("""
            <html><body style="font-family:sans-serif;padding:2rem">
                <h2>&#10060; Session expired</h2>
                <p>This login link has expired. Close this tab and try connecting again.</p>
            </body></html>
        """)

    try:
        GoogleDriveConnector.exchange_code(account_name, code, REDIRECT_URI)
    except Exception as e:
        return HTMLResponse(f"""
            <html><body style="font-family:sans-serif;padding:2rem">
                <h2>&#10060; Failed to connect Drive</h2>
                <p>{e}</p>
            </body></html>
        """)

    return HTMLResponse("""
        <html><body style="font-family:sans-serif;padding:2rem">
            <h2>&#9989; Google Drive connected!</h2>
            <p>You can close this tab and return to the app.</p>
        </body></html>
    """)


@router.post("/{account_name}/restore")
def restore_index(account_name: str):
    """
    Restore the Drive index from appDataFolder to local disk if it's missing.
    Called on app startup for each connected account.
    Token is already on disk for desktop — no Firestore needed.
    """
    source_id = f"gdrive:{account_name}"
    connector = GoogleDriveConnector(account_name)

    if not connector.token_path.exists():
        return {"restored": False, "reason": "no_token"}

    if get_index_path(source_id).exists():
        index = load_index(source_id)
        return {"restored": True, "files": len(index), "source": "local_cache"}

    content = connector.read_appdata_file(APPDATA_INDEX_FILENAME)
    if not content:
        return {"restored": False, "reason": "no_index"}

    index = json.loads(content)
    save_index(index, source_id)
    return {"restored": True, "files": len(index), "source": "appdata"}


@router.delete("/{account_name}")
def logout(account_name: str):
    source_id = f"gdrive:{account_name}"
    connector = GoogleDriveConnector(account_name)
    if not connector.token_path.exists():
        raise HTTPException(status_code=404, detail=f"No account found: {account_name}")
    index_path = get_index_path(source_id)
    index = load_index(source_id) if index_path.exists() else {}
    purged = len(index)
    connector.logout()
    if index_path.exists():
        index_path.unlink()
    return {"disconnected": account_name, "index_entries_removed": purged}
