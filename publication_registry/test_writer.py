"""Tests for publication_registry/writer.py (SPEC.md Data Model,
Milestone M1).

Covers write_record()'s five reconciliation outcomes (see its own
docstring): fresh write, unreadable-existing-file conflict, idempotent
success on full agreement, state-conflict on disagreement (most
importantly gate_status/block_reason — the case a naive "same identity
= safe retry" model would silently mask), and a content_id collision
between two logically different events (different identity).

mint_content_id() itself is unchanged from M1 and untested further here
(see its own existing coverage) — this file only covers write_record()'s
new reconciliation logic.
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
        content_id="20260924T090000",
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

    assert path == str(tmp_path / "20260924T090000.json")
    assert Path(path).exists()


# --- Outcome 2: existing file unreadable ----------------------------------


def test_existing_file_invalid_json_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    existing_path = tmp_path / "20260924T090000.json"
    existing_path.write_text("{not valid json", encoding="utf-8")
    original_bytes = existing_path.read_bytes()

    with pytest.raises(PublicationRegistryConflictError):
        writer.write_record(make_record())

    assert existing_path.read_bytes() == original_bytes


def test_existing_file_valid_json_but_not_a_publication_record_raises_and_preserves_bytes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    existing_path = tmp_path / "20260924T090000.json"
    existing_path.write_text(json.dumps({"unrelated": "shape"}), encoding="utf-8")
    original_bytes = existing_path.read_bytes()

    with pytest.raises(PublicationRegistryConflictError):
        writer.write_record(make_record())

    assert existing_path.read_bytes() == original_bytes


# --- Outcome 3: same identity, full agreement -> idempotent success ------


def test_same_identity_full_agreement_is_idempotent_success(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record()
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    # A retry: identical in every field except the timestamps, which are
    # explicitly excluded from every comparison.
    retry = make_record(
        published_at="2026-09-24T09:05:00+00:00",
        gate_evaluated_at="2026-09-24T09:04:00+00:00",
    )

    path = writer.write_record(retry)

    assert path == first_path
    assert Path(first_path).read_bytes() == original_bytes  # nothing overwritten


def test_same_identity_full_agreement_including_block_status(tmp_path, monkeypatch):
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


# --- Outcome 4: same identity, disagreement -> state conflict ------------


def test_same_identity_gate_status_disagreement_raises_and_preserves_bytes(
    tmp_path, monkeypatch
):
    """The case a naive same-identity=safe-retry model would silently
    mask: two calls describing the same (claim_id, platform) but one
    says pass and the other says block. Must never be idempotent
    success."""
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(gate_status="pass")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(gate_status="block", block_reason="No eligible claim.")

    with pytest.raises(PublicationRegistryConflictError, match="gate_status"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


def test_same_identity_block_reason_disagreement_raises_and_preserves_bytes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(gate_status="block", block_reason="No eligible claim.")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(gate_status="block", block_reason="Different reason entirely.")

    with pytest.raises(PublicationRegistryConflictError, match="block_reason"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


def test_same_identity_url_disagreement_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record()
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    conflicting = make_record(url="https://www.linkedin.com/posts/a-different-post")

    with pytest.raises(PublicationRegistryConflictError, match="url"):
        writer.write_record(conflicting)

    assert Path(first_path).read_bytes() == original_bytes


# --- Outcome 5: different identity, same content_id -> collision ---------


def test_different_claim_id_same_content_id_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(claim_id="20260811T165911_04")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    different_event = make_record(claim_id="20260811T165911_05")

    with pytest.raises(PublicationRegistryConflictError, match="different publication event"):
        writer.write_record(different_event)

    assert Path(first_path).read_bytes() == original_bytes


def test_different_platform_same_content_id_raises_and_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(writer, "OUTPUT_DIR", str(tmp_path))
    first = make_record(platform="linkedin")
    first_path = writer.write_record(first)
    original_bytes = Path(first_path).read_bytes()

    different_event = make_record(platform="habr", url="https://habr.com/p/example")

    with pytest.raises(PublicationRegistryConflictError, match="different publication event"):
        writer.write_record(different_event)

    assert Path(first_path).read_bytes() == original_bytes


# --- mint_content_id: unchanged from M1, kept as a smoke check -----------


def test_mint_content_id_still_matches_run_id_timestamp_format():
    from datetime import datetime, timezone

    fixed_now = datetime(2026, 9, 24, 9, 0, 0, tzinfo=timezone.utc)
    assert writer.mint_content_id(fixed_now) == "20260924T090000"
