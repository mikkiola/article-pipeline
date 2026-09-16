"""Tests for author/authoring_context.py — AuthoringContext, built
post-classification directly from CanonicalUnit + already-computed
claim_treatments (ADR-0045).

Deliberately lives in author/, not strategy_layer/: this file (and the
module it tests) is never imported by pre_filter.py, framing.py, or
write_verdict.py — the mandatory codebase-wide search before this
diff confirmed zero such imports exist, and the whole point of this
module's placement is that none ever can by accident.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "strategy_layer"))
from authoring_context import AuthoringContext, build_authoring_contexts  # noqa: E402
from contract import CanonicalUnit  # noqa: E402


def _unit(unit_id, metadata, corroboration_status="not_applicable"):
    return CanonicalUnit(
        unit_id=unit_id,
        source="collector",
        created_at="2026-09-15T00:00:00+00:00",
        integrity_status="valid",
        integrity_check_method="commit_count_reconciliation",
        corroboration_status=corroboration_status,
        assertion_text=None,
        metadata=metadata,
    )


def test_only_included_units_produce_a_context():
    units = [
        _unit("a", {"source_type": "collector_daily_brief", "repo": "article-pipeline", "commit_count": 2}),
        _unit("b", {"source_type": "collector_daily_brief", "repo": "brain", "commit_count": 0}),
    ]
    claim_treatments = [
        {"claim_id": "a", "final_classification": "include", "framing": "6 commits landed."},
        {"claim_id": "b", "final_classification": "exclude", "framing": None},
    ]
    contexts = build_authoring_contexts(units, claim_treatments)
    assert len(contexts) == 1
    assert contexts[0].claim_id == "a"


def test_daily_brief_unit_carries_commit_messages_and_diffstat():
    units = [
        _unit(
            "a",
            {
                "source_type": "collector_daily_brief",
                "repo": "article-pipeline",
                "commit_count": 2,
                "diffstat": 42,
                "files_touched": ["a.py", "b.py"],
                "commit_messages": ["fix: bug", "chore: bump"],
            },
        )
    ]
    claim_treatments = [
        {"claim_id": "a", "final_classification": "include", "framing": "2 commits landed."}
    ]
    contexts = build_authoring_contexts(units, claim_treatments)
    assert contexts[0].source_type == "collector_daily_brief"
    assert contexts[0].commit_messages == ["fix: bug", "chore: bump"]
    assert contexts[0].diffstat == 42
    assert contexts[0].files_touched == ["a.py", "b.py"]
    assert contexts[0].framing == "2 commits landed."


def test_manifest_unit_has_counts_not_raw_text():
    units = [
        _unit(
            "a",
            {
                "source_type": "collector_manifest",
                "repo": "article-pipeline",
                "commit_count": 6,
                "counts": {"value": 2, "explicit_service": 3, "default_service": 1},
            },
        )
    ]
    claim_treatments = [
        {"claim_id": "a", "final_classification": "include", "framing": "6 commits this week."}
    ]
    contexts = build_authoring_contexts(units, claim_treatments)
    assert contexts[0].source_type == "collector_manifest"
    assert contexts[0].counts == {"value": 2, "explicit_service": 3, "default_service": 1}
    assert contexts[0].commit_messages == []
    assert contexts[0].diffstat is None


def test_unit_with_no_matching_treatment_is_skipped_not_errored():
    units = [_unit("a", {"source_type": "collector_daily_brief", "repo": "x", "commit_count": 1})]
    contexts = build_authoring_contexts(units, claim_treatments=[])
    assert contexts == []


def test_authoring_context_rejects_unknown_field():
    with pytest.raises(ValidationError):
        AuthoringContext(
            claim_id="a",
            framing=None,
            source_type="collector_daily_brief",
            repo="x",
            commit_count=1,
            unexpected_field="surprise",
        )
