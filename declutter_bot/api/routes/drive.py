import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from declutter_bot.connectors.gdrive import GoogleDriveConnector

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
def login_callback(code: str, state: str):
    account_name = _pending.pop(state, None)
    if not account_name:
        raise HTTPException(status_code=400, detail="Invalid or expired state. Try logging in again.")

    try:
        GoogleDriveConnector.exchange_code(account_name, code, REDIRECT_URI)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to exchange code: {e}")

    # Return a simple HTML page so the browser tab shows a success message
    return HTMLResponse("""
        <html><body style="font-family:sans-serif;padding:2rem">
            <h2>✅ Google Drive connected!</h2>
            <p>You can close this tab and return to the app.</p>
        </body></html>
    """)


@router.delete("/{account_name}")
def logout(account_name: str):
    connector = GoogleDriveConnector(account_name)
    if not connector.token_path.exists():
        raise HTTPException(status_code=404, detail=f"No account found: {account_name}")
    purged = connector.logout()
    return {"disconnected": account_name, "index_entries_removed": purged}
