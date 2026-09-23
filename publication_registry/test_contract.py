"""Tests for publication_registry/contract.py — the PublicationRecord
schema (SPEC.md Data Model, Milestone M1).

TDD: block_reason's model_validator is exactly the kind of mechanism
docs/CONSTITUTION.md's TDD rule targets — its entire job is triggering
correctly under specific field-combination conditions (does this
actually reject an inconsistent record), not a static lookup. Same
class of test as strategy_layer/test_contract.py's own conditional-
field coverage for CanonicalUnit.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import PublicationRecord  # noqa: E402

BASE_KWARGS = dict(
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


def test_valid_pass_record_constructs():
    record = PublicationRecord(**BASE_KWARGS)
    assert record.content_id == "20260924T090000"
    assert record.platform == "linkedin"
    assert record.gate_status == "pass"
    assert record.block_reason is None


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        PublicationRecord(**{**BASE_KWARGS, "unexpected_field": "surprise"})


def test_frozen_blocks_mutation():
    record = PublicationRecord(**BASE_KWARGS)
    with pytest.raises(ValidationError):
        record.content_id = "changed"


def test_block_reason_required_when_gate_status_block():
    with pytest.raises(ValidationError, match="block_reason is required"):
        PublicationRecord(
            **{
                **BASE_KWARGS,
                "gate_status": "block",
                "block_reason": None,
            }
        )


def test_block_reason_must_be_null_when_gate_status_pass():
    with pytest.raises(ValidationError, match="must be null"):
        PublicationRecord(
            **{
                **BASE_KWARGS,
                "gate_status": "pass",
                "block_reason": "No eligible claim survived pre-filter.",
            }
        )


def test_block_record_with_reason_constructs():
    record = PublicationRecord(
        **{
            **BASE_KWARGS,
            "gate_status": "block",
            "block_reason": "No eligible claim survived pre-filter.",
        }
    )
    assert record.gate_status == "block"
    assert record.block_reason == "No eligible claim survived pre-filter."


def test_invalid_platform_literal_rejected():
    with pytest.raises(ValidationError):
        PublicationRecord(**{**BASE_KWARGS, "platform": "twitter"})


def test_invalid_gate_policy_literal_rejected():
    with pytest.raises(ValidationError):
        PublicationRecord(**{**BASE_KWARGS, "gate_policy": "R7"})


def test_r6_gate_policy_constructs():
    record = PublicationRecord(**{**BASE_KWARGS, "gate_policy": "R6"})
    assert record.gate_policy == "R6"
