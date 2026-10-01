"""Tests for habr_edit_capture/diff_capture.py — a fake Drive `service`
object (no real network call, no real credential) exercising the full
pairing/diff/idempotency/draft==final logic end-to-end against
synthetic data. Real Drive API calls are never made in this suite —
see this task's own report for what was, and was not, verified against
a live account.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diff_capture  # noqa: E402
import writer  # noqa: E402


class _FakeRequest:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeFiles:
    def __init__(self, list_by_query: dict, export_by_id: dict):
        self._list_by_query = list_by_query
        self._export_by_id = export_by_id

    def list(self, q, fields, pageToken=None):
        files = self._list_by_query.get(q, [])
        return _FakeRequest({"files": files})

    def export(self, fileId, mimeType):
        return _FakeRequest(self._export_by_id[fileId].encode("utf-8"))


class _FakeService:
    def __init__(self, list_by_query: dict, export_by_id: dict):
        self._files = _FakeFiles(list_by_query, export_by_id)

    def files(self):
        return self._files


def _folder_query(root_id: str) -> str:
    return (
        f"'{root_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )


def _files_query(folder_id: str) -> str:
    return f"'{folder_id}' in parents and trashed = false"


def _make_service(folder_id, article_files, draft_text, final_text):
    list_by_query = {
        _folder_query("root-folder"): [{"id": folder_id, "name": "2026-10-01 article"}],
        _files_query(folder_id): article_files,
    }
    export_by_id = {}
    for f in article_files:
        if f["name"].endswith("-draft"):
            export_by_id[f["id"]] = draft_text
        elif f["name"].endswith("-final"):
            export_by_id[f["id"]] = final_text
    return _FakeService(list_by_query, export_by_id)


def _article_files(final_modified_time: str):
    return [
        {"id": "file-draft-1", "name": "2026-10-01-draft", "modifiedTime": "2026-10-01T08:00:00.000Z"},
        {"id": "file-final-1", "name": "2026-10-01-final", "modifiedTime": final_modified_time},
    ]


# --- pairing -------------------------------------------------------------


def test_pair_draft_and_final_matches_shared_date_stem():
    files = [
        {"id": "a", "name": "2026-10-01-draft"},
        {"id": "b", "name": "2026-10-01-final"},
        {"id": "c", "name": "2026-09-15-draft"},  # no matching -final
    ]
    pairs = diff_capture._pair_draft_and_final(files)

    assert list(pairs.keys()) == ["2026-10-01"]
    assert pairs["2026-10-01"]["draft"]["id"] == "a"
    assert pairs["2026-10-01"]["final"]["id"] == "b"


# --- end-to-end: a real edit ----------------------------------------------


def test_run_capture_pass_writes_a_record_with_a_real_diff(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    service = _make_service(
        "folder-1",
        _article_files("2026-10-01T09:00:00.000Z"),
        draft_text="line one\nline two\n",
        final_text="line one\nline TWO edited\n",
    )

    report = diff_capture.run_capture_pass(service, "root-folder")

    assert len(report) == 1
    assert report[0]["written"] is not None

    records = writer.read_captures("folder-1", "2026-10-01")
    assert len(records) == 1
    assert records[0].has_changes is True
    assert "line TWO edited" in records[0].diff


# --- idempotency: same run fired twice against an unmodified file --------


def test_run_capture_pass_twice_against_unmodified_final_produces_one_record(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    service = _make_service(
        "folder-1",
        _article_files("2026-10-01T09:00:00.000Z"),
        draft_text="same text\n",
        final_text="same text, edited\n",
    )

    first_report = diff_capture.run_capture_pass(service, "root-folder")
    second_report = diff_capture.run_capture_pass(service, "root-folder")

    assert first_report[0]["written"] is not None
    assert second_report[0]["written"] is None  # idempotent no-op

    records = writer.read_captures("folder-1", "2026-10-01")
    assert len(records) == 1


# --- a real re-edit: same filename, new modifiedTime ----------------------


def test_run_capture_pass_detects_a_real_reedit_as_a_new_event(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))

    first_service = _make_service(
        "folder-1",
        _article_files("2026-10-01T09:00:00.000Z"),
        draft_text="draft text\n",
        final_text="first edit\n",
    )
    diff_capture.run_capture_pass(first_service, "root-folder")

    second_service = _make_service(
        "folder-1",
        _article_files("2026-10-01T15:30:00.000Z"),  # same filename, new modifiedTime
        draft_text="draft text\n",
        final_text="second, later edit\n",
    )
    second_report = diff_capture.run_capture_pass(second_service, "root-folder")

    assert second_report[0]["written"] is not None  # treated as a new event, not deduped

    records = writer.read_captures("folder-1", "2026-10-01")
    assert len(records) == 2


# --- draft == final --------------------------------------------------------


def test_run_capture_pass_writes_a_zero_diff_record_when_draft_equals_final(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    service = _make_service(
        "folder-1",
        _article_files("2026-10-01T09:00:00.000Z"),
        draft_text="published exactly as drafted\n",
        final_text="published exactly as drafted\n",
    )

    report = diff_capture.run_capture_pass(service, "root-folder")

    assert report[0]["written"] is not None  # still written — not treated as noise

    records = writer.read_captures("folder-1", "2026-10-01")
    assert len(records) == 1
    assert records[0].has_changes is False
    assert records[0].diff == ""
