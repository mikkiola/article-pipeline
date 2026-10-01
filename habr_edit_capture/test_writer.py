"""Tests for habr_edit_capture/writer.py — including the two scenarios
this task's verification requirements name explicitly: (1) the same
scheduled run firing twice against an unmodified `-final` file produces
exactly one record, and (2) the same filename with modified content
(a real re-edit, per Part 3's dedup-key design) produces a second,
distinct record.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import writer  # noqa: E402
from contract import HabrEditCaptureRecord  # noqa: E402


def make_record(**overrides) -> HabrEditCaptureRecord:
    kwargs = dict(
        folder_id="drive-folder-abc",
        folder_name="2026-10-01 article",
        date_stem="2026-10-01",
        draft_file_id="drive-file-draft-1",
        final_file_id="drive-file-final-1",
        final_modified_time="2026-10-01T09:00:00+00:00",
        diff="--- draft\n+++ final\n@@ -1 +1 @@\n-old\n+new\n",
        has_changes=True,
        captured_at="2026-10-01T10:00:00+00:00",
    )
    kwargs.update(overrides)
    return HabrEditCaptureRecord(**kwargs)


# --- write_capture(): basic write --------------------------------------


def test_no_existing_records_writes_and_returns_new_path(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    record = make_record()

    path = writer.write_capture(record)

    assert path is not None
    assert Path(path).exists()
    assert Path(path).parent == tmp_path / "drive-folder-abc" / "2026-10-01"
    assert Path(path).suffix == ".json"


def test_write_capture_creates_folder_id_and_date_stem_subdirectories(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    assert not (tmp_path / "drive-folder-abc" / "2026-10-01").exists()

    writer.write_capture(make_record())

    assert (tmp_path / "drive-folder-abc" / "2026-10-01").is_dir()


# --- idempotency: same scheduled run firing twice -----------------------


def test_same_run_fired_twice_against_unmodified_final_produces_one_record(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    record = make_record()

    first_path = writer.write_capture(record)
    second_result = writer.write_capture(record)

    assert first_path is not None
    assert second_result is None  # idempotent no-op, not a duplicate

    all_records = writer.read_captures("drive-folder-abc", "2026-10-01")
    assert len(all_records) == 1


def test_identical_final_modified_time_with_differently_built_record_is_still_deduped(
    tmp_path, monkeypatch
):
    """Guards against a dedup check that accidentally compares object
    identity or a uuid instead of final_modified_time: a record built
    fresh a second time (different captured_at, same final_modified_time)
    must still be treated as the same event."""
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))

    writer.write_capture(make_record(captured_at="2026-10-01T10:00:00+00:00"))
    result = writer.write_capture(make_record(captured_at="2026-10-01T10:05:00+00:00"))

    assert result is None
    assert len(writer.read_captures("drive-folder-abc", "2026-10-01")) == 1


# --- a real re-edit: same filename, new content/modifiedTime ------------


def test_reedit_with_new_modified_time_produces_a_second_record(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))

    first_path = writer.write_capture(
        make_record(final_modified_time="2026-10-01T09:00:00+00:00", diff="first diff")
    )
    second_path = writer.write_capture(
        make_record(final_modified_time="2026-10-01T15:30:00+00:00", diff="second diff")
    )

    assert first_path is not None
    assert second_path is not None
    assert first_path != second_path

    all_records = writer.read_captures("drive-folder-abc", "2026-10-01")
    assert len(all_records) == 2
    assert {r.diff for r in all_records} == {"first diff", "second diff"}


# --- read_captures(): absence is a complete, valid state ----------------


def test_read_captures_returns_empty_list_for_unknown_article(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    assert writer.read_captures("no-such-folder", "2026-01-01") == []


def test_read_captures_sorted_by_captured_at(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))

    writer.write_capture(
        make_record(
            final_modified_time="2026-10-01T15:30:00+00:00",
            captured_at="2026-10-01T16:00:00+00:00",
        )
    )
    writer.write_capture(
        make_record(
            final_modified_time="2026-10-01T09:00:00+00:00",
            captured_at="2026-10-01T10:00:00+00:00",
        )
    )

    records = writer.read_captures("drive-folder-abc", "2026-10-01")
    assert [r.captured_at.hour for r in records] == [10, 16]
