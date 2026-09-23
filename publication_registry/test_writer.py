"""Tests for publication_registry/writer.py (SPEC.md Data Model,
Milestone M1).

No RED-first TDD for write_record()'s collision check (see the M1
commit message for the judgment call): the check is a single,
structurally trivial condition (`if os.path.exists(path): raise`)
directly adapted from an already-working precedent
(strategy_layer/write_verdict.py), not a mechanism with subtle trigger
conditions. mint_content_id() is likewise a direct format-string
adaptation of this project's existing run_id convention, not a novel
mechanism.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import writer  # noqa: E402
from contract import PublicationRecord  # noqa: E402


def make_record(content_id: str = "20260924T090000", **overrides) -> PublicationRecord:
    kwargs = dict(
        content_id=content_id,
        platform="linkedin",
        url="https://www.linkedin.com/posts/example",
        published_at="2026-09-24T09:00:00+00:00",
        claim_id="20260811T165911_04",
        gate_policy="bootstrap",
        gate_version="v1",
        gate_status="pass",
        block_reason=None,
        gate_evaluated_at="2026-09-24T08:59:00+00:00",
    )
    kwargs.update(overrides)
    return PublicationRecord(**kwargs)


def test_mint_content_id_matches_run_id_timestamp_format():
    fixed_now = datetime(2026, 9, 24, 9, 0, 0, tzinfo=timezone.utc)
    assert writer.mint_content_id(fixed_now) == "20260924T090000"


def test_mint_content_id_normalizes_non_utc_input_to_utc():
    from datetime import timedelta, timezone as tz

    plus_three = tz(timedelta(hours=3))
    local_noon = datetime(2026, 9, 24, 12, 0, 0, tzinfo=plus_three)
    assert writer.mint_content_id(local_noon) == "20260924T090000"


def test_write_record_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    record = make_record()

    path = writer.write_record(record)

    assert path == str(tmp_path / "20260924T090000.json")
    written = Path(path).read_text(encoding="utf-8")
    assert '"content_id": "20260924T090000"' in written
    assert '"gate_status": "pass"' in written


def test_write_record_raises_on_content_id_collision_and_preserves_first_file(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first_record = make_record()
    path = writer.write_record(first_record)
    original_bytes = Path(path).read_bytes()

    second_record = make_record(url="https://www.linkedin.com/posts/different")

    with pytest.raises(FileExistsError):
        writer.write_record(second_record)

    assert Path(path).read_bytes() == original_bytes


def test_write_record_creates_output_dir_if_missing(tmp_path, monkeypatch):
    missing_dir = tmp_path / "not_yet_created"
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(missing_dir))
    record = make_record()

    path = writer.write_record(record)

    assert Path(path).exists()
