"""Tests for habr_edit_capture/drive_client.py's query/pagination/parsing
logic, against a fake Drive `service` object. `build_drive_service()`
itself (real credential loading + real `googleapiclient.discovery.build()`
call) is intentionally NOT exercised here — it needs a real service-account
key file and makes no sense to fake; see this task's own report for what
was, and was not, verified against a live account.
"""

import sys
from datetime import timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_client  # noqa: E402


class _FakeRequest:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeFiles:
    def __init__(self, pages: list[dict] | None = None, export_bytes: bytes | None = None):
        self._pages = pages or []
        self._export_bytes = export_bytes
        self.list_calls: list[dict] = []

    def list(self, q, fields, pageToken=None):
        self.list_calls.append({"q": q, "fields": fields, "pageToken": pageToken})
        index = len(self.list_calls) - 1
        return _FakeRequest(self._pages[index])

    def export(self, fileId, mimeType):
        self.export_file_id = fileId
        self.export_mime_type = mimeType
        return _FakeRequest(self._export_bytes)


class _FakeService:
    def __init__(self, files: _FakeFiles):
        self._files = files

    def files(self):
        return self._files


# --- list_child_folders ----------------------------------------------------


def test_list_child_folders_queries_for_folder_mimetype_under_root():
    fake_files = _FakeFiles(pages=[{"files": [{"id": "f1", "name": "folder one"}]}])
    service = _FakeService(fake_files)

    result = drive_client.list_child_folders(service, "root-id")

    assert result == [{"id": "f1", "name": "folder one"}]
    query = fake_files.list_calls[0]["q"]
    assert "'root-id' in parents" in query
    assert "mimeType = 'application/vnd.google-apps.folder'" in query
    assert "trashed = false" in query


def test_list_child_folders_follows_pagination():
    fake_files = _FakeFiles(
        pages=[
            {"files": [{"id": "f1", "name": "one"}], "nextPageToken": "tok2"},
            {"files": [{"id": "f2", "name": "two"}]},
        ]
    )
    service = _FakeService(fake_files)

    result = drive_client.list_child_folders(service, "root-id")

    assert [f["id"] for f in result] == ["f1", "f2"]
    assert fake_files.list_calls[1]["pageToken"] == "tok2"


# --- list_files_in_folder ---------------------------------------------------


def test_list_files_in_folder_requests_id_name_modifiedtime():
    fake_files = _FakeFiles(
        pages=[{"files": [{"id": "x", "name": "2026-10-01-draft", "modifiedTime": "2026-10-01T08:00:00.000Z"}]}]
    )
    service = _FakeService(fake_files)

    result = drive_client.list_files_in_folder(service, "folder-id")

    assert result[0]["id"] == "x"
    assert "modifiedTime" in fake_files.list_calls[0]["fields"]
    assert "'folder-id' in parents" in fake_files.list_calls[0]["q"]


# --- read_doc_text -----------------------------------------------------------


def test_read_doc_text_exports_as_plain_text_and_decodes():
    fake_files = _FakeFiles(export_bytes="привет, мир".encode("utf-8"))
    service = _FakeService(fake_files)

    text = drive_client.read_doc_text(service, "file-id")

    assert text == "привет, мир"
    assert fake_files.export_file_id == "file-id"
    assert fake_files.export_mime_type == "text/plain"


# --- parse_modified_time -----------------------------------------------------


def test_parse_modified_time_handles_z_suffix():
    result = drive_client.parse_modified_time("2026-10-01T09:00:00.000Z")
    assert result.year == 2026
    assert result.month == 10
    assert result.day == 1
    assert result.tzinfo is not None
    assert result.astimezone(timezone.utc).hour == 9
