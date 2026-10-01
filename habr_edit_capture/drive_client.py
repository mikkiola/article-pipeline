"""Habr Edit Capture — Google Drive API access (SPEC.md Functional
Requirement 21; SPEC.md Security Considerations).

Read-only, service-account credential (SPEC.md's own Tech
Stack/API Design/Security Considerations sections all independently
state this — not re-derived here; this task could not itself observe
how the owner accesses Drive today, since that requires her own
account, which this task has no access to). The owner must share her
existing per-Habr-article root folder with the service account's own
email address (standard Drive sharing) before this can read anything —
an owner-side manual step this module cannot perform or verify, same
class of gap `linkedin-daily-publish.yml` already flagged for
`GH_APP_ID`/`GH_APP_PRIVATE_KEY` not existing as secrets yet.

`build()`/`service_account.Credentials` signatures confirmed directly
against the installed `google-api-python-client==2.201.0`/
`google-auth==2.59.1` libraries this session, not assumed from
memory.

Every function here takes an already-built Drive `service` resource as
a parameter, never constructs one internally except in
`build_drive_service()` itself — this is what makes
`diff_capture.py`'s orchestration logic unit-testable against a fake
service object without a real credential or network call.
"""

from __future__ import annotations

from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Native Google Docs have no flat byte content to download via
# files.get(alt="media") (that path is for binary uploads only,
# confirmed against the Drive API v3 Files reference — the same
# reference that confirmed headRevisionId's binary-only limitation,
# contract.py's own docstring). A Google Doc must be exported instead.
_EXPORT_MIME_TYPE = "text/plain"


def build_drive_service(service_account_file: str):
    """Returns an authorized Drive v3 `service` resource built from a
    service-account JSON key file. Never called by anything in this
    package except the real scheduled-job entry point — every other
    function here takes `service` as a parameter instead, so tests can
    inject a fake one.
    """
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def list_child_folders(service, root_folder_id: str) -> list[dict]:
    """Returns every immediate child folder of `root_folder_id` — one
    entry per Habr article, per FR18's "each folder contains..."
    per-article convention. Each entry has at least `id` and `name`
    (Drive API v3 Files resource fields, confirmed against the live
    reference this session).
    """
    query = (
        f"'{root_folder_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )
    results: list[dict] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
            )
            .execute()
        )
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results


def list_files_in_folder(service, folder_id: str) -> list[dict]:
    """Returns every non-trashed file directly inside `folder_id`, with
    `id`, `name`, and `modifiedTime` — the three fields contract.py's
    dedup-key design depends on, confirmed available on both
    `files.get` and `files.list` against the live Drive API v3
    reference this session (unlike `headRevisionId`, which is
    binary-only and therefore not requested here).
    """
    query = f"'{folder_id}' in parents and trashed = false"
    results: list[dict] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, modifiedTime)",
                pageToken=page_token,
            )
            .execute()
        )
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results


def read_doc_text(service, file_id: str) -> str:
    """Exports a native Google Doc's content as plain text. Uses
    `files().export()`, not `files().get(alt="media")` — the latter is
    for binary Drive uploads only; a Google Doc has no flat byte
    content to download directly (same distinction contract.py's
    docstring already draws for `headRevisionId`).
    """
    raw = service.files().export(fileId=file_id, mimeType=_EXPORT_MIME_TYPE).execute()
    return raw.decode("utf-8") if isinstance(raw, bytes) else raw


def parse_modified_time(value: str) -> datetime:
    """Parses a Drive API `modifiedTime` string (RFC 3339, e.g.
    `2026-10-01T09:00:00.000Z`) into a timezone-aware `datetime` —
    `contract.py`'s `final_modified_time` field's own type.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
