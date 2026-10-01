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
        {"name": "article-pipeline", "commit_count": 2, "diffstat": 42,
         "files_touched": ["a.py", "b.py"], "commit_messages": ["fix: bug", "chore: bump"],
         "commit_evidence": []}
    ]
    assert result["commit_evidence"] == []


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


def test_mixed_contexts_deduplicates_identical_subject_lines():
    # Kept behavior: identical subject lines from two included repos
    # collapse to one entry in the merged output. (Units no longer share a
    # brief-wide list — each carries only its own repo's messages.)
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


def test_per_repo_entries_keep_each_repos_own_messages_without_cross_repo_dedup():
    # The flat top-level list collapses identical subjects across repos
    # (kept, other code reads it); per_repo must not, or a repo's own
    # attribution is lost and per-repo clustering has nothing to cluster.
    contexts = [
        AuthoringContext(
            claim_id="a", framing="f1", source_type="collector_daily_brief",
            repo="article-pipeline", commit_count=2,
            commit_messages=["fix: shared bug", "feat: only here"],
        ),
        AuthoringContext(
            claim_id="b", framing="f2", source_type="collector_daily_brief",
            repo="brain", commit_count=1,
            commit_messages=["fix: shared bug"],
        ),
    ]
    result = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-15")
    assert result["commit_messages"] == ["fix: shared bug", "feat: only here"]
    assert [(r["name"], r["commit_messages"]) for r in result["per_repo"]] == [
        ("article-pipeline", ["fix: shared bug", "feat: only here"]),
        ("brain", ["fix: shared bug"]),
    ]


def test_manifest_sourced_context_carries_an_empty_per_repo_message_list():
    contexts = [
        AuthoringContext(
            claim_id="a", framing="f", source_type="collector_manifest",
            repo="article-pipeline", commit_count=6, counts={"value": 2},
        )
    ]
    result = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-15")
    assert result["per_repo"][0]["commit_messages"] == []


def test_per_repo_message_list_is_a_copy_not_the_contexts_own_list():
    ctx = AuthoringContext(
        claim_id="a", framing="f", source_type="collector_daily_brief",
        repo="brain", commit_count=1, commit_messages=["fix: x"],
    )
    result = build_daily_brief_from_authoring_contexts([ctx], date="2026-09-15")
    result["per_repo"][0]["commit_messages"].append("mutated")
    assert ctx.commit_messages == ["fix: x"]


def test_empty_contexts_produces_idea_fallback_shape():
    result = build_daily_brief_from_authoring_contexts([], date="2026-09-15")
    assert result["mode"] == "idea_fallback"
    assert result["per_repo"] == []
    assert result["total_diffstat"] == 0


# --- commit_evidence (ADR-0057 point 4 / ADR-0059 activation, 2026-10-01) --


def test_commit_evidence_is_carried_through_top_level_and_per_repo():
    ctx = AuthoringContext(
        claim_id="a", framing="f", source_type="collector_daily_brief",
        repo="article-pipeline", commit_count=1, commit_messages=["feat: x"],
        commit_evidence=[{"sha": "1" * 40, "subject": "feat: x", "why": "needed for y", "effect": "y works"}],
    )
    result = build_daily_brief_from_authoring_contexts([ctx], date="2026-09-15")
    assert result["commit_evidence"] == [
        {"sha": "1" * 40, "subject": "feat: x", "why": "needed for y", "effect": "y works"}
    ]
    assert result["per_repo"][0]["commit_evidence"] == [
        {"sha": "1" * 40, "subject": "feat: x", "why": "needed for y", "effect": "y works"}
    ]


def test_commit_evidence_deduplicated_by_sha_not_subject():
    # Two different commits can share an identical subject; sha is the
    # dedup key here, unlike the flat commit_messages list above (which
    # dedups by subject text, kept for that field's own reasons).
    same_sha_entry = {"sha": "1" * 40, "subject": "feat: x", "why": "needed", "effect": "works"}
    contexts = [
        AuthoringContext(
            claim_id="a", framing="f1", source_type="collector_daily_brief",
            repo="article-pipeline", commit_count=1, commit_messages=["feat: x"],
            commit_evidence=[same_sha_entry],
        ),
        AuthoringContext(
            claim_id="b", framing="f2", source_type="collector_daily_brief",
            repo="brain", commit_count=1, commit_messages=["feat: x"],
            commit_evidence=[same_sha_entry],
        ),
    ]
    result = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-15")
    assert result["commit_evidence"] == [same_sha_entry]
    # Per-repo attribution is unaffected by the top-level dedup.
    assert result["per_repo"][0]["commit_evidence"] == [same_sha_entry]
    assert result["per_repo"][1]["commit_evidence"] == [same_sha_entry]


def test_manifest_sourced_context_carries_an_empty_commit_evidence_list():
    contexts = [
        AuthoringContext(
            claim_id="a", framing="f", source_type="collector_manifest",
            repo="article-pipeline", commit_count=6, counts={"value": 2},
        )
    ]
    result = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-15")
    assert result["commit_evidence"] == []
    assert result["per_repo"][0]["commit_evidence"] == []
