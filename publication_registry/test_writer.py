"""Tests for publication_registry/writer.py (SPEC.md Data Model,
Milestone M1; docs/adr/0053-content-id-ownership-moves-to-caller.md).

Covers write_record()'s four reconciliation outcomes (see its own
docstring): fresh write, unreadable-existing-file conflict, idempotent
success on full agreement (excluding the two timestamp fields), and a
state conflict on any other disagreement — including specifically
`claim_id`/`platform` disagreement, since content_id is now the
caller's own stable identity and any field mismatch once content_id
matches is simply a conflict, with no separate identity-vs-agreement
distinction (ADR-0053 collapses the old five-outcome model's split).

content_id is caller-supplied in every test below — there is no
mint_content_id() to call anymore (removed by ADR-0053); a fixed string
is used, matching what a real caller (M2/M4, not yet built) will
eventually supply.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import writer  # noqa: E402
from contract import PublicationRecord  # noqa: E402
from writer import PublicationRegistryConflictError  # noqa: E402


def make_record(**overrides) -> PublicationRecord:
    kwargs = dict(
        content_id="linkedin-20260811T165911_04-attempt1",
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


# --- Outcome 1: no existing file -----------------------------------------


def test_no_existing_file_writes_and_returns_new_path(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    record = make_record()

    path = writer.write_record(record)

    assert path == str(tmp_path / "linkedin-20260811T165911_04-attempt1.json")
    assert Path(path).exists()


# --- Outcome 2: existing file unreadable ----------------------------------


def test_existing_file_invalid_json_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    existing_path = tmp_path / "linkedin-20260811T165911_04-attempt1.json"
    existing_path.write_text("{not valid json", encoding="utf-8")
    original_bytes = existing_path.read_bytes()

    with pytest.raises(PublicationRegistryConflictError):
        writer.write_record(make_record())

    assert existing_path.read_bytes() == original_bytes


def test_existing_file_valid_json_but_not_a_publication_record_raises_and_preserves_bytes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    existing_path = tmp_path / "linkedin-20260811T165911_04-attempt1.json"
    existing_path.write_text(json.dumps({"unrelated": "shape"}), encoding="utf-8")
    original_bytes = existing_path.read_bytes()

    with pytest.raises(PublicationRegistryConflictError):
        writer.write_record(make_record())

    assert existing_path.read_bytes() == original_bytes


# --- Outcome 3: full agreement except timestamps -> idempotent success ---


def test_idempotent_retry_with_differing_timestamps_returns_existing_path_without_rewrite(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record()
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    # A retry: identical in every field except the timestamps, which are
    # explicitly excluded from comparison.
    retry = make_record(
        published_at="2026-09-24T09:05:00+00:00",
        gate_evaluated_at="2026-09-24T09:04:00+00:00",
    )

    path = writer.write_record(retry)

    assert path == first_path
    assert Path(first_path).read_bytes() == original_bytes  # nothing overwritten


def test_idempotent_retry_of_a_blocked_record(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(gate_status="block", block_reason="No eligible claim.")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    retry = make_record(
        gate_status="block",
        block_reason="No eligible claim.",
        published_at="2026-09-24T09:05:00+00:00",
    )

    path = writer.write_record(retry)

    assert path == first_path
    assert Path(first_path).read_bytes() == original_bytes


# --- Outcome 4: any other disagreement -> conflict ------------------------


def test_disagreement_on_gate_status_raises_and_preserves_bytes(tmp_path, monkeypatch):
    """The case a naive same-content_id=safe-retry model would silently
    mask: two calls for the same content_id, one says pass and the
    other says block. Must never be idempotent success."""
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(gate_status="pass")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(gate_status="block", block_reason="No eligible claim.")

    with pytest.raises(PublicationRegistryConflictError, match="gate_status"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


def test_disagreement_on_claim_id_raises_and_preserves_bytes(tmp_path, monkeypatch):
    """Collapsed case (ADR-0053): under the old five-outcome model this
    was "different identity"; now it's just another field disagreement
    under the same content_id — still a conflict, same as any other."""
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(claim_id="20260811T165911_04")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(claim_id="20260811T165911_05")

    with pytest.raises(PublicationRegistryConflictError, match="claim_id"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


def test_disagreement_on_platform_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(platform="linkedin")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(platform="habr", url="https://habr.com/p/example")

    with pytest.raises(PublicationRegistryConflictError, match="platform"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


def test_disagreement_on_url_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record()
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(url="https://www.linkedin.com/posts/a-different-post")

    with pytest.raises(PublicationRegistryConflictError, match="url"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


def test_disagreement_on_block_reason_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(gate_status="block", block_reason="No eligible claim.")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(gate_status="block", block_reason="Different reason entirely.")

    with pytest.raises(PublicationRegistryConflictError, match="block_reason"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


# --- read_record(): read-only lookup by content_id ------------------------


def test_read_record_returns_none_when_no_file_and_creates_nothing(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(output_dir))

    assert writer.read_record("linkedin-2026-09-24") is None
    assert not output_dir.exists()


def test_read_record_returns_parsed_record_and_leaves_file_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    record = make_record()
    path = Path(writer.write_record(record))
    original_bytes = path.read_bytes()
    original_mtime_ns = path.stat().st_mtime_ns

    result = writer.read_record(record.content_id)

    assert result == record
    assert path.read_bytes() == original_bytes
    assert path.stat().st_mtime_ns == original_mtime_ns


def test_read_record_raises_on_unreadable_file_instead_of_reporting_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    existing_path = tmp_path / "linkedin-2026-09-24.json"
    existing_path.write_text("{not valid json", encoding="utf-8")
    original_bytes = existing_path.read_bytes()

    with pytest.raises(PublicationRegistryConflictError):
        writer.read_record("linkedin-2026-09-24")

    assert existing_path.read_bytes() == original_bytes


def test_read_record_raises_on_valid_json_that_is_not_a_publication_record(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    (tmp_path / "linkedin-2026-09-24.json").write_text(
        json.dumps({"unrelated": "shape"}), encoding="utf-8"
    )

    with pytest.raises(PublicationRegistryConflictError):
        writer.read_record("linkedin-2026-09-24")
