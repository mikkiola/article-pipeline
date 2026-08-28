"""Tests for strategy_layer/pre_filter.py (SPEC.md Test Plan items 2-3,
Milestone M1).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pre_filter  # noqa: E402


def make_claim(claim_id: str, *, missing_context: bool = False) -> dict:
    return {
        "claim_id": claim_id,
        "extracted_at": "2026-08-28T00:00:00+00:00",
        "atom_path": "02_Cards/Example.md",
        "status": "claim",
        "confidence": None,
        "category": "wrong_framing",
        "reason": "",
        "context": None if missing_context else {"tags": [], "wiki_links": []},
    }


def make_evidence(claim_id: str, status: str) -> dict:
    return {
        "evidence_id": f"{claim_id}_ev",
        "run_id": "run1",
        "created_at": "2026-08-28T00:00:00+00:00",
        "claim_id": claim_id,
        "status": status,
        "searched_at": "2026-08-28T00:00:00+00:00",
        "search_query": "example query",
        "requests_used": 1,
        "source_url": None,
        "source_title": None,
        "license": None,
        "note": None,
    }


@pytest.mark.parametrize(
    "status,expected_classification",
    [
        ("verified", "include"),
        ("disputed", "exclude"),
        ("unverifiable", "exclude"),
        ("pending", "exclude"),
    ],
)
def test_pre_filter_table(status, expected_classification):
    claim = make_claim("c1")
    evidence = make_evidence("c1", status)

    result = pre_filter.classify_pair(claim, evidence)

    assert result["pre_filter_classification"] == expected_classification
    if expected_classification == "exclude":
        assert result["reason"] is not None
    else:
        assert result["reason"] is None


def test_missing_evidence_record_raises_naming_claim_id():
    claims = [make_claim("c1")]
    evidence_records = []

    with pytest.raises(ValueError, match="c1"):
        pre_filter.join_claims_and_evidence(claims, evidence_records)


def test_missing_context_field_raises_naming_claim_id_and_field():
    claims = [make_claim("c1", missing_context=True)]
    evidence_records = [make_evidence("c1", "verified")]

    with pytest.raises(ValueError, match=r"c1.*context"):
        pre_filter.join_claims_and_evidence(claims, evidence_records)


def test_full_run_mixed_statuses_no_exception_correct_classifications():
    claims = [make_claim("c1"), make_claim("c2"), make_claim("c3"), make_claim("c4")]
    evidence_records = [
        make_evidence("c1", "verified"),
        make_evidence("c2", "disputed"),
        make_evidence("c3", "unverifiable"),
        make_evidence("c4", "pending"),
    ]

    results = pre_filter.run_pre_filter(claims, evidence_records)
    by_claim_id = {r["claim_id"]: r for r in results}

    assert by_claim_id["c1"]["pre_filter_classification"] == "include"
    assert by_claim_id["c2"]["pre_filter_classification"] == "exclude"
    assert by_claim_id["c3"]["pre_filter_classification"] == "exclude"
    assert by_claim_id["c4"]["pre_filter_classification"] == "exclude"

    assert by_claim_id["c1"]["reason"] is None
    for claim_id in ("c2", "c3", "c4"):
        assert by_claim_id[claim_id]["reason"] is not None
