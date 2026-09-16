"""author/habr_verdict_to_story.py — HabrDigest built directly from a
list of AuthoringContext (ADR-0046, ADR-0045's pattern reused
unchanged), skipping story_builder.py's build_story()/CanonicalStory
entirely.

**Superseded design note (ADR-0046):** an earlier version of this
module built one CanonicalStory from exactly one included claim,
refusing (MultiClaimNotSupportedError) whenever a run had more than
one. A real end-to-end run against current Collector data
(strategy_layer/run_habr_pilot.py, manifest_2026-09-12.json) showed
that's not an edge case — a typical week produces multiple included
claims (5, in that real run) — so single-claim was replaced with a
multi-section digest, per ADR-0046.

Structural juxtaposition, not narrative synthesis: each section is one
already-vetted context's own framing text, listed under a shared
title — not combined into a new cross-claim claim. No new
derivation_kind check applies at the digest level; each context's own
framing was already checked (against strategy_layer/derivation_kind.py's
rule table) when it was produced, at the claim_treatments-building
stage.

**Russian-language safety net** (strategy_layer/language_check.py's
looks_russian()): checked per claim, not per run. A claim whose
framing fails is excluded from the digest with a printed reason — not
silently dropped, and not grounds to refuse the whole digest, mirroring
strategy_layer/pre_filter.py's own check_gate_condition()'s existing
"zero survivors refuses, partial survival doesn't" pattern. Only zero
surviving claims refuses the digest build entirely.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "strategy_layer"))
from authoring_context import AuthoringContext  # noqa: E402
from language_check import looks_russian  # noqa: E402


class HabrDigestSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    repo: str
    framing: str


class HabrDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sections: list[HabrDigestSection]


def build_habr_digest(contexts: list[AuthoringContext]) -> HabrDigest:
    """Builds one HabrDigest section per included AuthoringContext whose
    framing text is non-null and passes looks_russian(). A claim that
    fails either check is excluded (printed, not silent) rather than
    dropped without trace or forcing the whole digest to refuse.

    Raises ValueError if zero claims survive — genuinely nothing to
    publish, matching check_gate_condition()'s own "zero included
    units" refusal at the earlier pre-filter stage.
    """
    sections: list[HabrDigestSection] = []
    excluded: list[tuple[str, str]] = []

    for ctx in contexts:
        if not ctx.framing:
            excluded.append((ctx.claim_id, "no framing text"))
            continue
        if not looks_russian(ctx.framing):
            excluded.append((ctx.claim_id, "failed the Russian-language safety net (looks_russian())"))
            continue
        sections.append(HabrDigestSection(claim_id=ctx.claim_id, repo=ctx.repo, framing=ctx.framing))

    for claim_id, reason in excluded:
        print(f"WARNING: {claim_id} excluded from Habr digest — {reason}", file=sys.stderr)

    if not sections:
        raise ValueError(
            f"zero claims survived the digest build out of {len(contexts)} "
            f"included this run (excluded: {excluded}) — nothing to publish"
        )

    return HabrDigest(sections=sections)
