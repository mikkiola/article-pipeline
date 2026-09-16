"""Tests for strategy_layer/derivation_kind.py — the static rule-table
check that a declared derivation_kind is warranted by the framed unit's
source_status_snapshot (SPEC.md's "declarative derivation-kind
classification for framing text" extension).

TDD per docs/CONSTITUTION.md's TDD rule, same precedent as M2's
gate-check: this is a mechanism whose entire job is triggering
correctly under specific status/count combinations, not a mechanical
lookup with no conditional risk.

causal_claim is warranted only when source_corroboration_status ==
"corroborated" — every other status (not_applicable, pending,
disputed, unsubstantiated) is unconditionally unwarranted. Corrected
2026-09-15 from an earlier version of this rule that named only
not_applicable/pending; disputed/unsubstantiated were found to be an
unresolved gap in the original specification, then closed by the owner
(disputed/unsubstantiated are, if anything, weaker grounds for a
causal claim than not_applicable/pending, not stronger).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derivation_kind  # noqa: E402


def test_restatement_warranted_from_not_applicable():
    result = derivation_kind.check_derivation_warranted(
        "restatement", "not_applicable"
    )
    assert result == {"warranted": True, "reason": None}


def test_restatement_warranted_from_corroborated():
    result = derivation_kind.check_derivation_warranted(
        "restatement", "corroborated"
    )
    assert result == {"warranted": True, "reason": None}


def test_restatement_warranted_from_disputed():
    result = derivation_kind.check_derivation_warranted("restatement", "disputed")
    assert result == {"warranted": True, "reason": None}


def test_restatement_warranted_from_unsubstantiated():
    result = derivation_kind.check_derivation_warranted(
        "restatement", "unsubstantiated"
    )
    assert result == {"warranted": True, "reason": None}


def test_restatement_warranted_from_pending():
    result = derivation_kind.check_derivation_warranted("restatement", "pending")
    assert result == {"warranted": True, "reason": None}


def test_aggregation_unwarranted_with_single_unit():
    result = derivation_kind.check_derivation_warranted(
        "aggregation", "not_applicable", unit_count_in_run=1
    )
    assert result["warranted"] is False
    assert "only one source unit" in result["reason"]


def test_aggregation_warranted_with_multiple_units():
    result = derivation_kind.check_derivation_warranted(
        "aggregation", "not_applicable", unit_count_in_run=2
    )
    assert result == {"warranted": True, "reason": None}


def test_aggregation_default_unit_count_is_unwarranted():
    # unit_count_in_run defaults to 1 — a caller that forgets to pass it
    # gets the safe (unwarranted) answer, not a silent pass.
    result = derivation_kind.check_derivation_warranted("aggregation", "corroborated")
    assert result["warranted"] is False


def test_evaluation_warranted_from_corroborated():
    result = derivation_kind.check_derivation_warranted(
        "evaluation", "corroborated"
    )
    assert result == {"warranted": True, "reason": None}


def test_evaluation_unwarranted_from_not_applicable_without_aggregation_rule():
    result = derivation_kind.check_derivation_warranted(
        "evaluation", "not_applicable", has_defined_aggregation_rule=False
    )
    assert result["warranted"] is False
    assert "no defined aggregation rule" in result["reason"]


def test_evaluation_warranted_from_not_applicable_with_aggregation_rule():
    result = derivation_kind.check_derivation_warranted(
        "evaluation", "not_applicable", has_defined_aggregation_rule=True
    )
    assert result == {"warranted": True, "reason": None}


def test_evaluation_unwarranted_from_disputed():
    result = derivation_kind.check_derivation_warranted("evaluation", "disputed")
    assert result["warranted"] is False


def test_evaluation_unwarranted_from_unsubstantiated():
    result = derivation_kind.check_derivation_warranted(
        "evaluation", "unsubstantiated"
    )
    assert result["warranted"] is False


def test_evaluation_unwarranted_from_pending():
    result = derivation_kind.check_derivation_warranted("evaluation", "pending")
    assert result["warranted"] is False


def test_causal_claim_unwarranted_from_not_applicable():
    result = derivation_kind.check_derivation_warranted(
        "causal_claim", "not_applicable"
    )
    assert result["warranted"] is False
    assert "never warranted" in result["reason"]


def test_causal_claim_unwarranted_from_pending():
    result = derivation_kind.check_derivation_warranted("causal_claim", "pending")
    assert result["warranted"] is False
    assert "never warranted" in result["reason"]


def test_causal_claim_warranted_from_corroborated():
    result = derivation_kind.check_derivation_warranted(
        "causal_claim", "corroborated"
    )
    assert result == {"warranted": True, "reason": None}


def test_causal_claim_unwarranted_from_disputed():
    result = derivation_kind.check_derivation_warranted("causal_claim", "disputed")
    assert result["warranted"] is False
    assert "never warranted" in result["reason"]


def test_causal_claim_unwarranted_from_unsubstantiated():
    result = derivation_kind.check_derivation_warranted(
        "causal_claim", "unsubstantiated"
    )
    assert result["warranted"] is False
    assert "never warranted" in result["reason"]


def test_unknown_derivation_kind_raises():
    with pytest.raises(ValueError, match="unknown derivation_kind"):
        derivation_kind.check_derivation_warranted("speculation", "corroborated")
