"""
Tests for GoogleDriveConnector bug fixes:
- _get_service() uses google.auth.transport.httplib2.AuthorizedHttp (not creds.authorize)
- _get_service() sets 30-second timeout on httplib2.Http
- scan() calls on_progress callback after each page
- scan() works without on_progress (backward compat)
- delete_appdata_file() finds and deletes the appDataFolder file
- delete_appdata_file() is a no-op when file doesn't exist
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from declutter_bot.connectors.gdrive import GoogleDriveConnector, APPDATA_INDEX_FILENAME


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_connector(account_name: str = "school") -> GoogleDriveConnector:
    """Return a connector with _load_creds pre-patched (no real token file needed)."""
    return GoogleDriveConnector(account_name)


def _fake_creds():
    creds = MagicMock()
    creds.expired = False
    creds.refresh_token = "fake_refresh"
    creds.token = "fake_token"
    return creds


def _drive_file(file_id: str, name: str = "notes.pdf") -> dict:
    return {
        "id": file_id,
        "name": name,
        "mimeType": "application/pdf",
        "size": "1024",
        "md5Checksum": f"md5_{file_id}",
        "modifiedTime": "2024-01-01T00:00:00Z",
        "parents": ["root"],
        "webViewLink": f"https://drive.google.com/file/d/{file_id}/view",
    }


# ------------------------------------------------------------------
# _get_service — timeout and AuthorizedHttp
# ------------------------------------------------------------------

def test_get_service_uses_authorized_http_not_creds_authorize():
    """
    creds.authorize() is oauth2client API and doesn't exist in google-auth.
    _get_service() must use google.auth.transport.httplib2.AuthorizedHttp instead.
    """
    connector = _make_connector()
    fake_creds = _fake_creds()

    with patch.object(connector, "_load_creds", return_value=fake_creds), \
         patch("httplib2.Http") as mock_http_cls, \
         patch("google_auth_httplib2.AuthorizedHttp") as mock_authorized, \
         patch("googleapiclient.discovery.build") as mock_build:

        mock_http_cls.return_value = MagicMock()
        mock_authorized.return_value = MagicMock()
        mock_build.return_value = MagicMock()

        connector._get_service()

        # Must use AuthorizedHttp, not creds.authorize
        mock_authorized.assert_called_once()
        assert not hasattr(fake_creds, "authorize") or not fake_creds.authorize.called


def test_get_service_sets_30_second_timeout():
    connector = _make_connector()

    with patch.object(connector, "_load_creds", return_value=_fake_creds()), \
         patch("httplib2.Http") as mock_http_cls, \
         patch("google_auth_httplib2.AuthorizedHttp"), \
         patch("googleapiclient.discovery.build"):

        connector._get_service()

        mock_http_cls.assert_called_once_with(timeout=30)


def test_get_service_passes_authorized_http_to_build():
    connector = _make_connector()
    fake_authorized_http = MagicMock()

    with patch.object(connector, "_load_creds", return_value=_fake_creds()), \
         patch("httplib2.Http"), \
         patch("google_auth_httplib2.AuthorizedHttp", return_value=fake_authorized_http), \
         patch("googleapiclient.discovery.build") as mock_build:

        connector._get_service()

        mock_build.assert_called_once_with("drive", "v3", http=fake_authorized_http)


def test_get_service_is_cached():
    """_get_service() builds the service only once; second call returns the same object."""
    connector = _make_connector()

    with patch.object(connector, "_load_creds", return_value=_fake_creds()), \
         patch("httplib2.Http"), \
         patch("google_auth_httplib2.AuthorizedHttp"), \
         patch("googleapiclient.discovery.build") as mock_build:

        mock_build.return_value = MagicMock()

        svc1 = connector._get_service()
        svc2 = connector._get_service()

        assert svc1 is svc2
        assert mock_build.call_count == 1


# ------------------------------------------------------------------
# scan() — on_progress callback + pagination
# ------------------------------------------------------------------

def _make_mock_service(pages: list[list[dict]]) -> MagicMock:
    """
    Build a mock Drive service that returns paginated responses.
    pages: list of file lists; each becomes one API response page.
    """
    service = MagicMock()
    responses = []
    for i, page_files in enumerate(pages):
        resp = {"files": page_files}
        if i < len(pages) - 1:
            resp["nextPageToken"] = f"token_{i}"
        responses.append(resp)

    service.files.return_value.list.return_value.execute.side_effect = responses
    return service


def test_scan_returns_all_files_across_pages():
    connector = _make_connector()
    page1 = [_drive_file("id1"), _drive_file("id2")]
    page2 = [_drive_file("id3")]

    with patch.object(connector, "_get_service", return_value=_make_mock_service([page1, page2])):
        results = connector.scan()

    assert len(results) == 3
    ids = {r.path.name for r in results}
    assert ids == {"id1", "id2", "id3"}


def test_scan_calls_on_progress_after_each_page():
    connector = _make_connector()
    page1 = [_drive_file("id1"), _drive_file("id2")]
    page2 = [_drive_file("id3")]

    progress_calls = []

    with patch.object(connector, "_get_service", return_value=_make_mock_service([page1, page2])):
        connector.scan(on_progress=lambda count: progress_calls.append(count))

    # on_progress should have been called once per page with cumulative count
    assert progress_calls == [2, 3]


def test_scan_without_on_progress_does_not_raise():
    connector = _make_connector()
    page1 = [_drive_file("id1")]

    with patch.object(connector, "_get_service", return_value=_make_mock_service([page1])):
        results = connector.scan()  # no on_progress

    assert len(results) == 1


def test_scan_empty_drive_returns_empty_list():
    connector = _make_connector()

    with patch.object(connector, "_get_service", return_value=_make_mock_service([[]])):
        results = connector.scan()

    assert results == []


def test_scan_on_progress_called_with_whitelisted_count_only():
    """on_progress count reflects files that passed the whitelist filter, not raw Drive count."""
    connector = _make_connector()
    # .zip is not in DRIVE_EXT_WHITELIST, so it's filtered out
    page1 = [_drive_file("id1", "notes.pdf"), {"id": "id2", "name": "archive.zip",
             "mimeType": "application/zip", "size": "0",
             "modifiedTime": "2024-01-01T00:00:00Z", "parents": []}]

    progress_calls = []
    with patch.object(connector, "_get_service", return_value=_make_mock_service([page1])):
        connector.scan(on_progress=lambda count: progress_calls.append(count))

    # Only 1 file passes the whitelist
    assert progress_calls == [1]


# ------------------------------------------------------------------
# delete_appdata_file()
# ------------------------------------------------------------------

def _appdata_list_response(file_ids: list[str]) -> dict:
    return {"files": [{"id": fid} for fid in file_ids]}


def test_delete_appdata_file_deletes_found_file():
    connector = _make_connector()
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = (
        _appdata_list_response(["appdata_file_id"])
    )

    with patch.object(connector, "_get_service", return_value=service):
        connector.delete_appdata_file(APPDATA_INDEX_FILENAME)

    service.files.return_value.delete.assert_called_once_with(fileId="appdata_file_id")
    service.files.return_value.delete.return_value.execute.assert_called_once()


def test_delete_appdata_file_noop_when_not_found():
    connector = _make_connector()
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = (
        _appdata_list_response([])
    )

    with patch.object(connector, "_get_service", return_value=service):
        connector.delete_appdata_file(APPDATA_INDEX_FILENAME)

    service.files.return_value.delete.assert_not_called()


def test_delete_appdata_file_deletes_all_matching():
    """If multiple files share the same name (shouldn't happen, but be safe), delete all."""
    connector = _make_connector()
    service = MagicMock()
    service.files.return_value.list.return_value.execute.return_value = (
        _appdata_list_response(["id_a", "id_b"])
    )

    with patch.object(connector, "_get_service", return_value=service):
        connector.delete_appdata_file(APPDATA_INDEX_FILENAME)

    assert service.files.return_value.delete.call_count == 2
    service.files.return_value.delete.assert_any_call(fileId="id_a")
    service.files.return_value.delete.assert_any_call(fileId="id_b")
