"""Tests for strategy_layer/contract.py — the canonical Pydantic input
contract (SPEC.md's Data Model, Milestone M1).

TDD: CanonicalUnit's model_validator is exactly the kind of mechanism
docs/CONSTITUTION.md's TDD rule targets — its entire job is triggering
correctly under specific field-combination conditions (does this
actually reject an inconsistent record), not a static lookup.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import CanonicalUnit  # noqa: E402

BASE_KWARGS = dict(
    unit_id="c1",
    source="collector",
    created_at="2026-09-15T00:00:00+00:00",
    integrity_status="valid",
    integrity_check_method="ancestry_reconciliation",
    corroboration_status="not_applicable",
    assertion_text=None,
    metadata={},
)


def test_valid_not_applicable_unit_constructs():
    unit = CanonicalUnit(**BASE_KWARGS)
    assert unit.unit_id == "c1"
    assert unit.corroboration_status == "not_applicable"
    assert unit.assertion_text is None


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        CanonicalUnit(**{**BASE_KWARGS, "unexpected_field": "surprise"})


def test_frozen_blocks_mutation():
    unit = CanonicalUnit(**BASE_KWARGS)
    with pytest.raises(ValidationError):
        unit.unit_id = "changed"


def test_assertion_text_required_when_corroboration_status_not_not_applicable():
    with pytest.raises(ValidationError, match="assertion_text is required"):
        CanonicalUnit(
            **{
                **BASE_KWARGS,
                "corroboration_status": "corroborated",
                "assertion_text": None,
                "source_url": "https://example.com",
                "license": "CC-BY",
            }
        )


def test_assertion_text_must_be_null_when_not_applicable():
    with pytest.raises(ValidationError, match="must be null"):
        CanonicalUnit(
            **{**BASE_KWARGS, "assertion_text": "this should not be set"}
        )


def test_corroborated_requires_source_url_and_license():
    with pytest.raises(ValidationError, match="source_url and license are required"):
        CanonicalUnit(
            **{
                **BASE_KWARGS,
                "corroboration_status": "corroborated",
                "assertion_text": "Activity increased.",
                "source_url": None,
                "license": None,
            }
        )


def test_corroborated_with_source_url_and_license_constructs():
    unit = CanonicalUnit(
        **{
            **BASE_KWARGS,
            "corroboration_status": "corroborated",
            "assertion_text": "Activity increased.",
            "source_url": "https://example.com/study",
            "license": "CC-BY-4.0",
        }
    )
    assert unit.corroboration_status == "corroborated"


def test_invalid_source_literal_rejected():
    with pytest.raises(ValidationError):
        CanonicalUnit(**{**BASE_KWARGS, "source": "not_a_real_source"})


def test_invalid_integrity_status_literal_rejected():
    with pytest.raises(ValidationError):
        CanonicalUnit(**{**BASE_KWARGS, "integrity_status": "maybe"})


def test_disputed_does_not_require_source_url_or_license():
    # R8 only constrains corroborated units — disputed/unsubstantiated/
    # pending units may cite source_url/license but aren't required to.
    unit = CanonicalUnit(
        **{
            **BASE_KWARGS,
            "corroboration_status": "disputed",
            "assertion_text": "Some contested claim.",
        }
    )
    assert unit.source_url is None
    assert unit.license is None
