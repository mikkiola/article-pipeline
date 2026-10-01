"""Tests for habr_edit_capture/contract.py."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import HabrEditCaptureRecord  # noqa: E402


def make_record(**overrides) -> HabrEditCaptureRecord:
    kwargs = dict(
        folder_id="drive-folder-abc",
        folder_name="2026-10-01 — Как мы...",
        date_stem="2026-10-01",
        draft_file_id="drive-file-draft-1",
        final_file_id="drive-file-final-1",
        final_modified_time="2026-10-01T09:00:00+00:00",
        diff="--- draft\n+++ final\n@@ -1 +1 @@\n-old line\n+new line\n",
        has_changes=True,
        captured_at="2026-10-01T10:00:00+00:00",
    )
    kwargs.update(overrides)
    return HabrEditCaptureRecord(**kwargs)


def test_valid_record_constructs():
    record = make_record()
    assert record.folder_id == "drive-folder-abc"
    assert record.has_changes is True


def test_record_is_frozen():
    record = make_record()
    with pytest.raises(ValidationError):
        record.diff = "changed"


def test_extra_field_forbidden():
    with pytest.raises(ValidationError):
        make_record(unexpected_field="nope")


def test_zero_diff_capture_is_representable():
    record = make_record(diff="", has_changes=False)
    assert record.diff == ""
    assert record.has_changes is False


def test_folder_name_may_be_none():
    record = make_record(folder_name=None)
    assert record.folder_name is None


@pytest.mark.parametrize(
    "missing_field",
    [
        "folder_id",
        "date_stem",
        "draft_file_id",
        "final_file_id",
        "final_modified_time",
        "diff",
        "has_changes",
        "captured_at",
    ],
)
def test_missing_required_field_rejected(missing_field):
    kwargs = dict(
        folder_id="drive-folder-abc",
        folder_name="title",
        date_stem="2026-10-01",
        draft_file_id="drive-file-draft-1",
        final_file_id="drive-file-final-1",
        final_modified_time="2026-10-01T09:00:00+00:00",
        diff="",
        has_changes=False,
        captured_at="2026-10-01T10:00:00+00:00",
    )
    del kwargs[missing_field]
    with pytest.raises(ValidationError):
        HabrEditCaptureRecord(**kwargs)
