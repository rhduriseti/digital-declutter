"""
Tests for scan_state.py — in-memory job tracking (desktop, no Firestore).
"""
import declutter_bot.api.scan_state as scan_state
import pytest


@pytest.fixture(autouse=True)
def reset_in_memory(monkeypatch):
    monkeypatch.setattr(scan_state, "_jobs", {})


# ------------------------------------------------------------------
# Basic lifecycle
# ------------------------------------------------------------------

def test_create_job_returns_string_id():
    job_id = scan_state.create_job()
    assert isinstance(job_id, str) and len(job_id) > 0


def test_create_job_status_is_running():
    job_id = scan_state.create_job()
    assert scan_state.get_job(job_id)["status"] == "running"


def test_get_job_returns_none_for_unknown_id():
    assert scan_state.get_job("nonexistent-id") is None


def test_set_done_marks_job_done():
    job_id = scan_state.create_job()
    scan_state.set_done(job_id, {"total_files": 42})
    job = scan_state.get_job(job_id)
    assert job["status"] == "done"
    assert job["result"]["total_files"] == 42


def test_set_error_marks_job_error():
    job_id = scan_state.create_job()
    scan_state.set_error(job_id, "Drive API timeout")
    job = scan_state.get_job(job_id)
    assert job["status"] == "error"
    assert job["error"] == "Drive API timeout"


def test_set_done_includes_warnings():
    job_id = scan_state.create_job()
    scan_state.set_done(job_id, {}, warnings=["skipped 3 files"])
    assert "skipped 3 files" in scan_state.get_job(job_id)["warnings"]


def test_set_done_clears_progress():
    job_id = scan_state.create_job()
    scan_state.set_progress(job_id, 10, 100, "file.pdf")
    scan_state.set_done(job_id, {})
    assert scan_state.get_job(job_id)["progress"] is None


# ------------------------------------------------------------------
# Progress
# ------------------------------------------------------------------

def test_set_progress_updates_job():
    job_id = scan_state.create_job()
    scan_state.set_progress(job_id, 50, 200, "notes.pdf")
    progress = scan_state.get_job(job_id)["progress"]
    assert progress["files_scanned"] == 50
    assert progress["total"] == 200
    assert progress["current_file"] == "notes.pdf"


def test_set_progress_calculates_percent():
    job_id = scan_state.create_job()
    scan_state.set_progress(job_id, 75, 300, "")
    assert scan_state.get_job(job_id)["progress"]["percent"] == 25


def test_set_progress_zero_total_gives_zero_percent():
    job_id = scan_state.create_job()
    scan_state.set_progress(job_id, 0, 0, "")
    assert scan_state.get_job(job_id)["progress"]["percent"] == 0


def test_set_progress_noop_for_unknown_job():
    scan_state.set_progress("ghost-id", 5, 10, "x")  # should not raise
