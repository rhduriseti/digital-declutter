"""
End-to-end scan tests for the desktop pipeline:

  POST /scan  →  background job  →  GET /scan/status/{job_id}  →  done

Drive API is fully mocked. No Firestore, no auth tokens.

Scenarios covered:
  - Drive scan: job created → files fetched → indexed → appdata written → done
  - Drive scan: connector raises → job marked as error
  - Drive scan: on_progress callback fires during pagination
  - Local scan: folder counted → files scanned → indexed → done
  - Local scan: missing folder → 400
  - Status endpoint: unknown job ID → {"status": "done"} (not 404)
  - Status endpoint: running job returns current state
  - POST /scan with Drive source wires on_progress into scan_state
  - Two Drive accounts produce independent indexes
  - Drive disconnect clears token and local index
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import declutter_bot.api.scan_state as scan_state
from declutter_bot.api.app import app
from declutter_bot.api.routes.scan import _run_drive_scan, _run_local_scan
from declutter_bot.core.index_manager import load_index, save_index


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_scan_state(monkeypatch):
    monkeypatch.setattr(scan_state, "_jobs", {})


@pytest.fixture()
def isolated_index(tmp_path, monkeypatch):
    monkeypatch.setattr("declutter_bot.core.paths.DATA_DIR", tmp_path)
    monkeypatch.setattr("declutter_bot.core.index_manager.DRIVE_ACCOUNTS_DIR", tmp_path)
    monkeypatch.setattr("declutter_bot.connectors.gdrive.DRIVE_ACCOUNTS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _mock_connector(pages: list[list[dict]], account_name: str = "school") -> MagicMock:
    connector = MagicMock()
    connector.account_name = account_name
    connector.token_path = MagicMock()
    connector.token_path.exists.return_value = True

    def fake_scan(on_progress=None):
        from declutter_bot.core.file_metadata import FileMetadata
        results = []
        for page in pages:
            for f in page:
                results.append(FileMetadata(
                    path=Path(f"gdrive:{account_name}/{f['id']}"),
                    name=f["name"],
                    extension=Path(f["name"]).suffix,
                    size_bytes=int(f.get("size", 0)),
                    created_at=None,
                    modified_at=None,
                    source=f"gdrive:{account_name}",
                    md5=f.get("md5Checksum"),
                    web_view_link=f.get("webViewLink"),
                ))
            if on_progress:
                on_progress(len(results))
        return results

    connector.scan.side_effect = fake_scan
    connector.write_appdata_file = MagicMock()
    connector.read_appdata_file = MagicMock(return_value=None)
    return connector


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


# ==================================================================
# _run_drive_scan
# ==================================================================

class TestRunDriveScan:

    def test_job_marked_done_after_successful_scan(self, isolated_index):
        job_id = scan_state.create_job()
        connector = _mock_connector([[_drive_file("id1"), _drive_file("id2")]])

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            _run_drive_scan(job_id, "school")

        job = scan_state.get_job(job_id)
        assert job["status"] == "done"
        assert job["result"] is not None

    def test_job_result_contains_file_count(self, isolated_index):
        job_id = scan_state.create_job()
        connector = _mock_connector([[_drive_file(f"id{i}") for i in range(5)]])

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            _run_drive_scan(job_id, "school")

        assert scan_state.get_job(job_id)["result"]["total_files"] == 5

    def test_job_marked_error_when_connector_raises(self, isolated_index):
        job_id = scan_state.create_job()
        connector = MagicMock()
        connector.read_appdata_file.return_value = None
        connector.scan.side_effect = Exception("Drive API timeout")

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            _run_drive_scan(job_id, "school")

        job = scan_state.get_job(job_id)
        assert job["status"] == "error"
        assert "Drive API timeout" in job["error"]

    def test_appdata_written_after_scan(self, isolated_index):
        job_id = scan_state.create_job()
        connector = _mock_connector([[_drive_file("id1"), _drive_file("id2")]])

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            _run_drive_scan(job_id, "school")

        connector.write_appdata_file.assert_called_once()
        filename, content = connector.write_appdata_file.call_args[0]
        assert filename == "claire_index.json"
        assert len(json.loads(content)) == 2

    def test_on_progress_called_during_pagination(self, isolated_index):
        job_id = scan_state.create_job()
        page1 = [_drive_file("id1"), _drive_file("id2")]
        page2 = [_drive_file("id3")]
        connector = _mock_connector([page1, page2])

        progress_snapshots = []
        original = scan_state.set_progress

        def recording_set_progress(jid, files_scanned, total, current_file):
            progress_snapshots.append((files_scanned, total))
            original(jid, files_scanned, total, current_file)

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector), \
             patch("declutter_bot.api.routes.scan.scan_state.set_progress", side_effect=recording_set_progress):
            _run_drive_scan(job_id, "school")

        # Pagination phase: total=0
        pagination_calls = [(s, t) for s, t in progress_snapshots if t == 0]
        assert pagination_calls == [(2, 0), (3, 0)]

        # Classification phase: total>0
        classification_calls = [(s, t) for s, t in progress_snapshots if t > 0]
        assert len(classification_calls) == 3
        assert classification_calls[-1] == (3, 3)

    def test_progress_cleared_on_done(self, isolated_index):
        job_id = scan_state.create_job()
        connector = _mock_connector([[_drive_file("id1")]])

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            _run_drive_scan(job_id, "school")

        assert scan_state.get_job(job_id)["progress"] is None

    def test_two_accounts_produce_independent_jobs(self, isolated_index):
        job_school = scan_state.create_job()
        job_personal = scan_state.create_job()
        c_school = _mock_connector([[_drive_file("s1"), _drive_file("s2")]], "school")
        c_personal = _mock_connector([[_drive_file("p1")]], "personal")

        def make_connector(account_name):
            return c_school if account_name == "school" else c_personal

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", side_effect=make_connector):
            _run_drive_scan(job_school, "school")
            _run_drive_scan(job_personal, "personal")

        assert scan_state.get_job(job_school)["result"]["total_files"] == 2
        assert scan_state.get_job(job_personal)["result"]["total_files"] == 1


# ==================================================================
# _run_local_scan
# ==================================================================

class TestRunLocalScan:

    def test_local_scan_job_done_after_scan(self, isolated_index, tmp_path):
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "essay.pdf").write_bytes(b"content")
        (folder / "notes.txt").write_bytes(b"notes")

        job_id = scan_state.create_job()
        _run_local_scan(job_id, str(folder))

        assert scan_state.get_job(job_id)["status"] == "done"

    def test_local_scan_result_has_file_count(self, isolated_index, tmp_path):
        folder = tmp_path / "docs"
        folder.mkdir()
        for i in range(3):
            (folder / f"file{i}.txt").write_bytes(b"x")

        job_id = scan_state.create_job()
        _run_local_scan(job_id, str(folder))

        assert scan_state.get_job(job_id)["result"]["total_files"] == 3

    def test_local_scan_error_on_bad_folder(self, isolated_index):
        job_id = scan_state.create_job()
        _run_local_scan(job_id, "/nonexistent/path/that/does/not/exist")

        assert scan_state.get_job(job_id)["status"] == "error"

    def test_local_scan_progress_fires_during_scan(self, isolated_index, tmp_path):
        folder = tmp_path / "docs"
        folder.mkdir()
        for i in range(4):
            (folder / f"file{i}.txt").write_bytes(b"x")

        job_id = scan_state.create_job()
        progress_seen = []

        original = scan_state.set_progress

        def capture(jid, files_scanned, total, current_file):
            progress_seen.append((files_scanned, total))
            original(jid, files_scanned, total, current_file)

        with patch("declutter_bot.api.routes.scan.scan_state.set_progress", side_effect=capture):
            _run_local_scan(job_id, str(folder))

        assert any(scanned > 0 for scanned, _ in progress_seen)


# ==================================================================
# GET /scan/status
# ==================================================================

class TestScanStatusEndpoint:

    def test_unknown_job_id_returns_done_not_404(self, client):
        resp = client.get("/scan/status/does-not-exist")
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

    def test_known_job_id_returns_running(self, client):
        job_id = scan_state.create_job()
        resp = client.get(f"/scan/status/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_known_job_id_returns_done_after_completion(self, client):
        job_id = scan_state.create_job()
        scan_state.set_done(job_id, {"total_files": 7})
        data = client.get(f"/scan/status/{job_id}").json()
        assert data["status"] == "done"
        assert data["result"]["total_files"] == 7

    def test_known_job_id_returns_error_status(self, client):
        job_id = scan_state.create_job()
        scan_state.set_error(job_id, "Drive quota exceeded")
        data = client.get(f"/scan/status/{job_id}").json()
        assert data["status"] == "error"
        assert "Drive quota exceeded" in data["error"]

    def test_status_returns_progress_fields(self, client):
        job_id = scan_state.create_job()
        scan_state.set_progress(job_id, 50, 200, "essay.pdf")
        progress = client.get(f"/scan/status/{job_id}").json()["progress"]
        assert progress["files_scanned"] == 50
        assert progress["total"] == 200
        assert progress["current_file"] == "essay.pdf"
        assert progress["percent"] == 25


# ==================================================================
# POST /scan
# ==================================================================

class TestPostScanEndpoint:

    def test_post_scan_local_returns_job_id(self, client, isolated_index, tmp_path):
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "a.txt").write_bytes(b"hello")

        resp = client.post("/scan", json={"folder": str(folder), "source": "local"})
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "running"

    def test_post_scan_local_background_runs_to_done(self, client, isolated_index, tmp_path):
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "essay.pdf").write_bytes(b"content")

        resp = client.post("/scan", json={"folder": str(folder), "source": "local"})
        job_id = resp.json()["job_id"]

        # TestClient runs background tasks synchronously
        assert client.get(f"/scan/status/{job_id}").json()["status"] == "done"

    def test_post_scan_local_missing_folder_param_returns_400(self, client, isolated_index):
        resp = client.post("/scan", json={"source": "local"})
        assert resp.status_code == 400

    def test_post_scan_drive_returns_job_id(self, client, isolated_index):
        connector = _mock_connector([[_drive_file("id1")]])

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            resp = client.post("/scan", json={"source": "gdrive:school"})

        assert resp.status_code == 200
        assert "job_id" in resp.json()

    def test_post_scan_drive_background_runs_to_done(self, client, isolated_index):
        files = [_drive_file(f"id{i}") for i in range(3)]
        connector = _mock_connector([files])

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            resp = client.post("/scan", json={"source": "gdrive:school"})
            job_id = resp.json()["job_id"]

        status = client.get(f"/scan/status/{job_id}").json()
        assert status["status"] == "done"
        assert status["result"]["total_files"] == 3

    def test_post_scan_drive_error_propagates_to_job(self, client, isolated_index):
        connector = MagicMock()
        connector.read_appdata_file.return_value = None
        connector.scan.side_effect = Exception("Auth failed")

        with patch("declutter_bot.api.routes.scan.GoogleDriveConnector", return_value=connector):
            resp = client.post("/scan", json={"source": "gdrive:school"})
            job_id = resp.json()["job_id"]

        status = client.get(f"/scan/status/{job_id}").json()
        assert status["status"] == "error"
        assert "Auth failed" in status["error"]


# ==================================================================
# Drive disconnect
# ==================================================================

class TestDriveDisconnect:

    def test_disconnect_returns_200(self, client, isolated_index):
        mock_connector = MagicMock()
        mock_connector.token_path.exists.return_value = True

        with patch("declutter_bot.api.routes.drive.GoogleDriveConnector", return_value=mock_connector):
            resp = client.delete("/drive/school")

        assert resp.status_code == 200
        assert resp.json()["disconnected"] == "school"

    def test_disconnect_calls_logout(self, client, isolated_index):
        mock_connector = MagicMock()
        mock_connector.token_path.exists.return_value = True

        with patch("declutter_bot.api.routes.drive.GoogleDriveConnector", return_value=mock_connector):
            client.delete("/drive/school")

        mock_connector.logout.assert_called_once()

    def test_disconnect_unknown_account_returns_404(self, client, isolated_index):
        mock_connector = MagicMock()
        mock_connector.token_path.exists.return_value = False

        with patch("declutter_bot.api.routes.drive.GoogleDriveConnector", return_value=mock_connector):
            resp = client.delete("/drive/ghost")

        assert resp.status_code == 404

    def test_disconnect_purges_local_index(self, client, isolated_index):
        save_index(
            {"gdrive:school/id1": {"name": "a.pdf", "source": "gdrive:school"}},
            "gdrive:school",
        )
        mock_connector = MagicMock()
        mock_connector.token_path.exists.return_value = True

        with patch("declutter_bot.api.routes.drive.GoogleDriveConnector", return_value=mock_connector):
            resp = client.delete("/drive/school")

        assert resp.json()["index_entries_removed"] == 1
