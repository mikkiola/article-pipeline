"""Tests for verdict/contract.py — the VerdictRecord schema (SPEC.md
Data Model, Milestone M3).
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import VerdictRecord  # noqa: E402

BASE_KWARGS = dict(
    content_id="linkedin-2026-09-29",
    verdict_type="good",
    received_at="2026-09-30T09:00:00+00:00",
    comment=None,
)


def test_valid_record_constructs():
    record = VerdictRecord(**BASE_KWARGS)
    assert record.content_id == "linkedin-2026-09-29"
    assert record.verdict_type == "good"
    assert record.comment is None


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        VerdictRecord(**{**BASE_KWARGS, "unexpected_field": "surprise"})


def test_frozen_blocks_mutation():
    record = VerdictRecord(**BASE_KWARGS)
    with pytest.raises(ValidationError):
        record.content_id = "changed"


def test_invalid_verdict_type_literal_rejected():
    with pytest.raises(ValidationError):
        VerdictRecord(**{**BASE_KWARGS, "verdict_type": "meh"})


def test_trash_verdict_type_constructs():
    record = VerdictRecord(**{**BASE_KWARGS, "verdict_type": "trash"})
    assert record.verdict_type == "trash"


def test_style_off_verdict_type_constructs():
    record = VerdictRecord(**{**BASE_KWARGS, "verdict_type": "style-off"})
    assert record.verdict_type == "style-off"


def test_comment_can_be_provided():
    record = VerdictRecord(
        **{**BASE_KWARGS, "comment": "Great problem->search->solution structure."}
    )
    assert record.comment == "Great problem->search->solution structure."


def test_comment_defaults_to_none_when_omitted():
    kwargs = {k: v for k, v in BASE_KWARGS.items() if k != "comment"}
    record = VerdictRecord(**kwargs)
    assert record.comment is None
