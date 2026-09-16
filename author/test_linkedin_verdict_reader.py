"""Tests for author/linkedin_verdict_reader.py — converts a run's
AuthoringContext list into the daily_brief-shaped dict
daily_linkedin_author.py's existing prompt builders already expect,
unchanged (M4, closes the direct-Collector-read bypass).

Named "verdict_reader" per SPEC.md's original Migration Sequence
naming; its actual input is AuthoringContext (ADR-0045), not a raw
verdict.json read from disk — see authoring_context.py's own
docstring for why a persisted verdict alone can't carry this data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authoring_context import AuthoringContext  # noqa: E402
from linkedin_verdict_reader import build_daily_brief_from_authoring_contexts  # noqa: E402


def test_daily_brief_sourced_context_populates_real_fields():
    contexts = [
        AuthoringContext(
            claim_id="a",
            framing="2 commits landed.",
            source_type="collector_daily_brief",
            repo="article-pipeline",
            commit_count=2,
            diffstat=42,
            files_touched=["a.py", "b.py"],
            commit_messages=["fix: bug", "chore: bump"],
        )
    ]
    result = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-15")
    assert result["mode"] == "fact"
    assert result["date"] == "2026-09-15"
    assert result["total_diffstat"] == 42
    assert result["files_touched"] == ["a.py", "b.py"]
    assert result["commit_messages"] == ["fix: bug", "chore: bump"]
    assert result["per_repo"] == [
        {"name": "article-pipeline", "commit_count": 2, "diffstat": 42, "files_touched": ["a.py", "b.py"]}
    ]


def test_manifest_sourced_context_has_no_raw_text_falls_back_to_idea_fallback_mode():
    contexts = [
        AuthoringContext(
            claim_id="a",
            framing="6 commits this week.",
            source_type="collector_manifest",
            repo="article-pipeline",
            commit_count=6,
            counts={"value": 2},
        )
    ]
    result = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-15")
    assert result["mode"] == "idea_fallback"
    assert result["commit_messages"] == []
    assert result["total_diffstat"] == 0


def test_mixed_contexts_deduplicates_shared_commit_messages():
    # Two daily_brief-sourced repos in the same run share the identical
    # top-level commit_messages list (see collector.py's own docstring
    # note on this) — must not appear duplicated in the merged output.
    contexts = [
        AuthoringContext(
            claim_id="a", framing="f1", source_type="collector_daily_brief",
            repo="article-pipeline", commit_count=2,
            commit_messages=["fix: shared bug"],
        ),
        AuthoringContext(
            claim_id="b", framing="f2", source_type="collector_daily_brief",
            repo="brain", commit_count=1,
            commit_messages=["fix: shared bug"],
        ),
    ]
    result = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-15")
    assert result["commit_messages"] == ["fix: shared bug"]
    assert len(result["per_repo"]) == 2


def test_empty_contexts_produces_idea_fallback_shape():
    result = build_daily_brief_from_authoring_contexts([], date="2026-09-15")
    assert result["mode"] == "idea_fallback"
    assert result["per_repo"] == []
    assert result["total_diffstat"] == 0
