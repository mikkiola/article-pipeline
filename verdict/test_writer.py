"""Tests for verdict/writer.py (SPEC.md Data Model, Milestone M3;
ADR-0050 point 1, confirmed current and unchanged by ADR-0052).

Owner Verdict is an append-only event stream, not a one-record-per-key
registry (contrast publication_registry/test_writer.py's four
reconciliation outcomes) — write_verdict() never reconciles against an
existing record; it always creates a new one. Coverage here mirrors
publication_registry/test_writer.py's shape only where it actually
applies: fresh write, and the read-side no-record/has-records split
that stands in for publication_registry's read_record() coverage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import writer  # noqa: E402
from contract import VerdictRecord  # noqa: E402


def make_record(**overrides) -> VerdictRecord:
    kwargs = dict(
        content_id="linkedin-2026-09-29",
        verdict_type="good",
        received_at="2026-09-30T09:00:00+00:00",
        comment=None,
    )
    kwargs.update(overrides)
    return VerdictRecord(**kwargs)


# --- write_verdict(): always appends a new file ----------------------------


def test_no_existing_records_writes_and_returns_new_path(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    record = make_record()

    path = writer.write_verdict(record)

    assert Path(path).exists()
    assert Path(path).parent == tmp_path / "linkedin-2026-09-29"
    assert Path(path).suffix == ".json"


def test_write_verdict_creates_content_id_subdirectory(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    assert not (tmp_path / "linkedin-2026-09-29").exists()

    writer.write_verdict(make_record())

    assert (tmp_path / "linkedin-2026-09-29").is_dir()


def test_multiple_appends_for_same_content_id_create_separate_files(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))

    first_path = writer.write_verdict(make_record(verdict_type="trash"))
    second_path = writer.write_verdict(
        make_record(verdict_type="good", comment="Fixed in the next post.")
    )

    assert first_path != second_path
    assert Path(first_path).exists()
    assert Path(second_path).exists()
    content_dir = tmp_path / "linkedin-2026-09-29"
    assert len(list(content_dir.glob("*.json"))) == 2


def test_written_file_round_trips_through_read_verdicts(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    record = make_record(verdict_type="style-off", comment="Hook was flat.")

    writer.write_verdict(record)

    [result] = writer.read_verdicts("linkedin-2026-09-29")
    assert result == record


# --- read_verdicts(): the `recorded` / `missing` split -------------------


def test_read_verdicts_returns_empty_list_when_no_directory_and_creates_nothing(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))

    result = writer.read_verdicts("linkedin-2026-09-28")

    assert result == []
    assert not (tmp_path / "linkedin-2026-09-28").exists()


def test_read_verdicts_returns_all_records_ordered_by_received_at(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    later = make_record(received_at="2026-09-30T12:00:00+00:00", verdict_type="good")
    earlier = make_record(received_at="2026-09-30T08:00:00+00:00", verdict_type="trash")

    # Written out of order on purpose, to confirm read_verdicts() sorts.
    writer.write_verdict(later)
    writer.write_verdict(earlier)

    result = writer.read_verdicts("linkedin-2026-09-29")

    assert [r.verdict_type for r in result] == ["trash", "good"]


def test_read_verdicts_for_unrelated_content_id_does_not_see_other_records(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    writer.write_verdict(make_record(content_id="linkedin-2026-09-29"))

    result = writer.read_verdicts("linkedin-2026-09-28")

    assert result == []
