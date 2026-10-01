"""Habr Edit Capture — orchestration (SPEC.md Functional Requirements
17-21; ADR-0050 point 4).

`run_capture_pass()` is what the scheduled job (Part 2;
`.github/workflows/habr-edit-capture.yml`) actually calls. It takes an
already-built Drive `service` (see `drive_client.build_drive_service()`)
and the owner's root folder id, and:

1. Lists every immediate child folder of the root — one per Habr
   article (FR18).
2. Within each, pairs up `<date-stem>-draft`/`<date-stem>-final` files
   by their shared date-stem.
3. For every such pair, reads both texts, diffs them
   (`difflib.unified_diff`), and calls `writer.write_capture()` —
   which itself performs the idempotency check against
   `final_modified_time` (contract.py's dedup key), so a repeated run
   against an unchanged `-final` file writes nothing new.

Deliberately NOT a general-purpose "watch everything, always" poller:
this function does one pass and returns a report of what it did,
leaving scheduling (how often, via what trigger) entirely to the
GitHub Actions workflow that calls it — matching
`linkedin_publisher/daily_publish.py`'s own one-pass-per-invocation
shape, not a long-running daemon.
"""

from __future__ import annotations

import difflib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_client  # noqa: E402
import writer  # noqa: E402
from contract import HabrEditCaptureRecord  # noqa: E402

_DRAFT_SUFFIX = "-draft"
_FINAL_SUFFIX = "-final"


def _pair_draft_and_final(files: list[dict]) -> dict[str, dict]:
    """Groups `files` (each a dict with at least `id`/`name`) by their
    shared date-stem, keeping only stems that have both a `-draft` and
    a `-final` file — FR18's own pairing convention. Returns
    {date_stem: {"draft": <file>, "final": <file>}}.
    """
    by_stem: dict[str, dict] = {}
    for f in files:
        name = f["name"]
        if name.endswith(_DRAFT_SUFFIX):
            stem = name[: -len(_DRAFT_SUFFIX)]
            by_stem.setdefault(stem, {})["draft"] = f
        elif name.endswith(_FINAL_SUFFIX):
            stem = name[: -len(_FINAL_SUFFIX)]
            by_stem.setdefault(stem, {})["final"] = f

    return {
        stem: pair
        for stem, pair in by_stem.items()
        if "draft" in pair and "final" in pair
    }


def _build_record(
    service, folder: dict, date_stem: str, draft_file: dict, final_file: dict
) -> HabrEditCaptureRecord:
    draft_text = drive_client.read_doc_text(service, draft_file["id"])
    final_text = drive_client.read_doc_text(service, final_file["id"])

    diff_lines = list(
        difflib.unified_diff(
            draft_text.splitlines(keepends=True),
            final_text.splitlines(keepends=True),
            fromfile=f"{date_stem}-draft",
            tofile=f"{date_stem}-final",
        )
    )
    diff_text = "".join(diff_lines)

    return HabrEditCaptureRecord(
        folder_id=folder["id"],
        folder_name=folder.get("name"),
        date_stem=date_stem,
        draft_file_id=draft_file["id"],
        final_file_id=final_file["id"],
        final_modified_time=drive_client.parse_modified_time(final_file["modifiedTime"]),
        diff=diff_text,
        has_changes=bool(diff_text),
        captured_at=datetime.now(timezone.utc),
    )


def run_capture_pass(service, root_folder_id: str) -> list[dict]:
    """Runs one capture pass. Returns a list of per-pair report dicts:
    `{"folder_id", "date_stem", "written": <path or None>}` —
    `written` is `None` exactly when `writer.write_capture()`'s own
    idempotency check found this `-final` state already captured.
    """
    report: list[dict] = []

    for folder in drive_client.list_child_folders(service, root_folder_id):
        files = drive_client.list_files_in_folder(service, folder["id"])
        for date_stem, pair in _pair_draft_and_final(files).items():
            record = _build_record(service, folder, date_stem, pair["draft"], pair["final"])
            written_path = writer.write_capture(record)
            report.append(
                {
                    "folder_id": folder["id"],
                    "date_stem": date_stem,
                    "written": written_path,
                }
            )

    return report
