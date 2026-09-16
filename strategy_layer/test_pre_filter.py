"""Tests for strategy_layer/pre_filter.py — the two-dimension
classification table and gate condition (SPEC.md's source-independence
extension, Milestone M2).

Rewritten 2026-09-15 for the two-dimension (integrity_status,
corroboration_status) model, replacing the old single-status
verified/disputed/unverifiable/pending table. The old
join_claims_and_evidence()-based tests (missing-evidence-record,
missing-context-field) are removed from this file — that join no
longer happens in pre_filter.py at all; each adapter is now
responsible for producing a complete CanonicalUnit per record
(Pydantic's own construction-time validation, see test_contract.py,
is the input-validation gate now).

TDD per docs/CONSTITUTION.md's TDD rule, same precedent as the
original gate-check: the gate condition specifically (does "gated"
actually fire under the right condition, and not fire otherwise) is
the mechanism whose entire job is triggering correctly. The
classification table itself is a direct, static lookup — tested
thoroughly here, but not RED-first-mandatory per SPEC.md's own
Non-Functional Requirement 2.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pre_filter  # noqa: E402
from contract import CanonicalUnit  # noqa: E402


def _unit(unit_id, integrity_status, corroboration_status, **overrides):
    kwargs = dict(
        unit_id=unit_id,
        source="collector",
        created_at=datetime.now(timezone.utc),
        integrity_status=integrity_status,
        integrity_check_method="commit_count_reconciliation",
        corroboration_status=corroboration_status,
        assertion_text=None if corroboration_status == "not_applicable" else "Some assertion.",
        metadata={},
    )
    kwargs.update(overrides)
    return CanonicalUnit(**kwargs)


# --- Classification table -------------------------------------------------


def test_invalid_integrity_excludes_regardless_of_corroboration():
    for corroboration_status in (
        "corroborated",
        "disputed",
        "unsubstantiated",
        "pending",
        "not_applicable",
    ):
        overrides = {}
        if corroboration_status == "corroborated":
            overrides = {"source_url": "https://example.com", "license": "CC-BY"}
        unit = _unit("u1", "invalid", corroboration_status, **overrides)
        result = pre_filter.classify_unit(unit)
        assert result["pre_filter_classification"] == "exclude", corroboration_status
        assert result["reason"] is not None


def test_valid_corroborated_includes():
    unit = _unit(
        "u2", "valid", "corroborated",
        source_url="https://example.com", license="CC-BY",
    )
    result = pre_filter.classify_unit(unit)
    assert result == {"claim_id": "u2", "pre_filter_classification": "include", "reason": None}


def test_valid_not_applicable_includes():
    unit = _unit("u3", "valid", "not_applicable")
    result = pre_filter.classify_unit(unit)
    assert result == {"claim_id": "u3", "pre_filter_classification": "include", "reason": None}


def test_valid_disputed_excludes():
    unit = _unit("u4", "valid", "disputed")
    result = pre_filter.classify_unit(unit)
    assert result["pre_filter_classification"] == "exclude"
    assert result["reason"] is not None


def test_valid_unsubstantiated_excludes():
    unit = _unit("u5", "valid", "unsubstantiated")
    result = pre_filter.classify_unit(unit)
    assert result["pre_filter_classification"] == "exclude"
    assert result["reason"] is not None


def test_valid_pending_excludes():
    unit = _unit("u6", "valid", "pending")
    result = pre_filter.classify_unit(unit)
    assert result["pre_filter_classification"] == "exclude"
    assert result["reason"] is not None


def test_run_pre_filter_classifies_every_unit():
    units = [
        _unit("a", "valid", "not_applicable"),
        _unit("b", "valid", "disputed"),
        _unit("c", "invalid", "not_applicable"),
    ]
    results = pre_filter.run_pre_filter(units)
    assert [r["claim_id"] for r in results] == ["a", "b", "c"]
    assert [r["pre_filter_classification"] for r in results] == [
        "include",
        "exclude",
        "exclude",
    ]


# --- Gate condition (TDD, per Non-Functional Requirement 1) --------------


def test_gate_fires_when_zero_included_units():
    results = [
        pre_filter.classify_unit(_unit("a", "valid", "disputed")),
        pre_filter.classify_unit(_unit("b", "invalid", "not_applicable")),
    ]
    gate_result = pre_filter.check_gate_condition(results)
    assert gate_result == {"status": "gated", "gates": {"zero_included_units": True}}


def test_gate_does_not_fire_with_one_included_among_excluded():
    results = [
        pre_filter.classify_unit(_unit("a", "valid", "not_applicable")),
        pre_filter.classify_unit(_unit("b", "valid", "disputed")),
    ]
    gate_result = pre_filter.check_gate_condition(results)
    assert gate_result == {"status": "normal", "gates": {"zero_included_units": False}}


def test_gate_does_not_fire_when_all_included():
    results = [
        pre_filter.classify_unit(_unit("a", "valid", "not_applicable")),
        pre_filter.classify_unit(
            _unit("b", "valid", "corroborated", source_url="https://x.com", license="CC0")
        ),
    ]
    gate_result = pre_filter.check_gate_condition(results)
    assert gate_result == {"status": "normal", "gates": {"zero_included_units": False}}


def test_gate_does_not_fire_on_empty_run():
    # Preserves the old gate's defensive convention: an empty run isn't
    # "everything got excluded," there's simply nothing to gate.
    gate_result = pre_filter.check_gate_condition([])
    assert gate_result == {"status": "normal", "gates": {"zero_included_units": False}}
