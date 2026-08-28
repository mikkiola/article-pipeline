"""Tests for strategy_layer/framing.py (SPEC.md Test Plan item 5,
Milestone M3).

Covers the mechanical half of Stage 2 — build_claim_treatment()'s
override-mandatory-reason enforcement (Functional Requirement #5) and
derive_overrides() — with the same TDD rigor as M2's gate-check
(docs/CONSTITUTION.md's TDD rule: a mechanism whose entire job is
enforcing a condition, where "does this actually trigger" is the
central risk). decide_framing() itself is Claude Code's interactive
judgment seam (see framing.py's docstring) and is not unit-testable
the same way — it is only checked here for existing as a deliberately
unimplemented seam, not accidentally auto-implemented or deleted.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import framing  # noqa: E402


def test_decide_framing_is_the_interactive_seam_not_auto_implemented():
    claim = {"claim_id": "c1", "context": {"tags": [], "wiki_links": []}}
    evidence = {"claim_id": "c1", "status": "verified"}

    with pytest.raises(NotImplementedError):
        framing.decide_framing(claim, evidence)


def test_bare_include_no_override():
    result = framing.build_claim_treatment(
        claim_id="c1",
        pre_filter_classification="include",
        pre_filter_reason=None,
        framing="A grounded, non-sensational framing of c1's claim.",
    )

    assert result == {
        "claim_id": "c1",
        "pre_filter_classification": "include",
        "final_classification": "include",
        "framing": "A grounded, non-sensational framing of c1's claim.",
        "reason": None,
    }


def test_bare_exclude_no_override_reuses_pre_filter_reason():
    result = framing.build_claim_treatment(
        claim_id="c2",
        pre_filter_classification="exclude",
        pre_filter_reason="No evidence found; accuracy not established.",
    )

    assert result == {
        "claim_id": "c2",
        "pre_filter_classification": "exclude",
        "final_classification": "exclude",
        "framing": None,
        "reason": "No evidence found; accuracy not established.",
    }


def test_override_exclude_to_include_uses_override_reason_not_pre_filter_reason():
    result = framing.build_claim_treatment(
        claim_id="c3",
        pre_filter_classification="exclude",
        pre_filter_reason="No evidence found; accuracy not established.",
        final_classification="include",
        framing="Reported as a live, honestly-labeled open question.",
        override_reason=(
            "Strong corroborating context.wiki_links despite unverifiable "
            "search evidence; honestly reportable as a live open question."
        ),
    )

    assert result["final_classification"] == "include"
    assert result["framing"] == "Reported as a live, honestly-labeled open question."
    assert result["reason"] == (
        "Strong corroborating context.wiki_links despite unverifiable "
        "search evidence; honestly reportable as a live open question."
    )
    assert result["reason"] != "No evidence found; accuracy not established."


def test_override_include_to_exclude_forces_framing_null():
    result = framing.build_claim_treatment(
        claim_id="c4",
        pre_filter_classification="include",
        pre_filter_reason=None,
        final_classification="exclude",
        framing="This framing text must be discarded, not carried through.",
        override_reason="Owner judged this framing dishonestly editorializes despite verified evidence.",
    )

    assert result["final_classification"] == "exclude"
    assert result["framing"] is None
    assert result["reason"] == (
        "Owner judged this framing dishonestly editorializes despite verified evidence."
    )


def test_override_without_reason_raises():
    with pytest.raises(ValueError, match="c5"):
        framing.build_claim_treatment(
            claim_id="c5",
            pre_filter_classification="exclude",
            pre_filter_reason="Not yet resolved; do not publish prematurely.",
            final_classification="include",
            framing="Some framing.",
            override_reason=None,
        )


def test_override_with_empty_string_reason_raises():
    with pytest.raises(ValueError, match="c6"):
        framing.build_claim_treatment(
            claim_id="c6",
            pre_filter_classification="include",
            pre_filter_reason=None,
            final_classification="exclude",
            override_reason="",
        )


def test_include_without_framing_raises():
    with pytest.raises(ValueError, match="c7"):
        framing.build_claim_treatment(
            claim_id="c7",
            pre_filter_classification="include",
            pre_filter_reason=None,
            framing=None,
        )


def test_derive_overrides_extracts_only_overridden_entries():
    claim_treatments = [
        framing.build_claim_treatment(
            claim_id="c1",
            pre_filter_classification="include",
            pre_filter_reason=None,
            framing="Bare include, no override.",
        ),
        framing.build_claim_treatment(
            claim_id="c2",
            pre_filter_classification="exclude",
            pre_filter_reason="No evidence found; accuracy not established.",
        ),
        framing.build_claim_treatment(
            claim_id="c3",
            pre_filter_classification="exclude",
            pre_filter_reason="No evidence found; accuracy not established.",
            final_classification="include",
            framing="Reported as a live, honestly-labeled open question.",
            override_reason="Strong corroborating context.wiki_links.",
        ),
    ]

    overrides = framing.derive_overrides(claim_treatments)

    assert overrides == [
        {
            "claim_id": "c3",
            "pre_filter_classification": "exclude",
            "final_classification": "include",
            "reason": "Strong corroborating context.wiki_links.",
        }
    ]


def test_derive_overrides_empty_when_no_overrides():
    claim_treatments = [
        framing.build_claim_treatment(
            claim_id="c1",
            pre_filter_classification="include",
            pre_filter_reason=None,
            framing="Bare include, no override.",
        ),
        framing.build_claim_treatment(
            claim_id="c2",
            pre_filter_classification="exclude",
            pre_filter_reason="Not yet resolved; do not publish prematurely.",
        ),
    ]

    assert framing.derive_overrides(claim_treatments) == []
