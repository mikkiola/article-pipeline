"""Tests for author/habr_verdict_to_story.py — HabrDigest built
directly from a list of AuthoringContext (ADR-0046, superseding this
task's earlier single-claim CanonicalStory design after a real run
showed it fails against realistic data — see ADR-0046's Context).

Structural juxtaposition, not narrative synthesis: each section is one
already-vetted context's own framing text, listed, not combined into
a new cross-claim claim — so no new derivation_kind check applies at
the digest level (each context's own framing was already checked when
produced).
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authoring_context import AuthoringContext  # noqa: E402
from habr_verdict_to_story import (  # noqa: E402
    HabrDigest,
    HabrDigestSection,
    build_habr_digest,
)

RUSSIAN_1 = "В репозитории article-pipeline было 6 коммит(ов) за последние 7 дней."
RUSSIAN_2 = "В репозитории brain было 5 коммит(ов) за последние 7 дней."
RUSSIAN_3 = "В репозитории radar было 2 коммит(ов) за последние 7 дней."
ENGLISH = "There were 6 commits in article-pipeline this week."


def _ctx(claim_id, framing, repo):
    return AuthoringContext(
        claim_id=claim_id, framing=framing, source_type="collector_manifest",
        repo=repo, commit_count=1, counts={"value": 1},
    )


def test_single_claim_still_works_as_a_one_section_digest():
    digest = build_habr_digest([_ctx("a", RUSSIAN_1, "article-pipeline")])
    assert len(digest.sections) == 1
    assert digest.sections[0].framing == RUSSIAN_1
    assert digest.sections[0].repo == "article-pipeline"


def test_five_real_claims_all_represented_not_truncated():
    contexts = [
        _ctx("a", RUSSIAN_1, "article-pipeline"),
        _ctx("b", RUSSIAN_2, "brain"),
        _ctx("c", RUSSIAN_3, "radar"),
        _ctx("d", "В репозитории archi-kg было 0 коммит(ов).", "archi-kg"),
        _ctx("e", "В репозитории tooltempest было 2 коммит(ов).", "tooltempest"),
    ]
    digest = build_habr_digest(contexts)
    assert len(digest.sections) == 5
    assert {s.repo for s in digest.sections} == {
        "article-pipeline", "brain", "radar", "archi-kg", "tooltempest"
    }


def test_zero_contexts_raises():
    with pytest.raises(ValueError, match="zero claims"):
        build_habr_digest([])


def test_non_russian_claim_excluded_not_whole_digest_refused():
    # Mirrors check_gate_condition()'s own "zero survivors refuses,
    # partial survival doesn't" precedent, applied here.
    contexts = [
        _ctx("a", RUSSIAN_1, "article-pipeline"),
        _ctx("b", ENGLISH, "brain"),
    ]
    digest = build_habr_digest(contexts)
    assert len(digest.sections) == 1
    assert digest.sections[0].repo == "article-pipeline"


def test_all_claims_non_russian_raises():
    contexts = [_ctx("a", ENGLISH, "article-pipeline")]
    with pytest.raises(ValueError, match="zero claims"):
        build_habr_digest(contexts)


def test_none_framing_excluded_like_non_russian():
    contexts = [
        _ctx("a", RUSSIAN_1, "article-pipeline"),
        _ctx("b", None, "brain"),
    ]
    digest = build_habr_digest(contexts)
    assert len(digest.sections) == 1


def test_habr_digest_section_rejects_unknown_field():
    with pytest.raises(ValidationError):
        HabrDigestSection(claim_id="a", repo="x", framing="y", extra_field="z")


def test_habr_digest_rejects_unknown_field():
    with pytest.raises(ValidationError):
        HabrDigest(sections=[], extra_field="z")
