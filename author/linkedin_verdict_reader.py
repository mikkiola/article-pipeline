"""author/linkedin_verdict_reader.py — AuthoringContext -> daily_brief-
shaped dict, the input daily_linkedin_author.py's existing prompt
builders (_build_fact_prompt/_build_idea_fallback_prompt) already
expect, unchanged.

Named "verdict_reader" per SPEC.md's original Migration Sequence
naming — its actual input is a list[AuthoringContext] (ADR-0045), not
a raw verdict.json read from disk. AuthoringContext already carries
everything a completed classification run produces (framing, raw
per-repo metadata); a persisted verdict.json's claim_treatments alone
lack that metadata (see ADR-0045's Context section), so this module
reads AuthoringContext instead of re-reading a verdict file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authoring_context import AuthoringContext  # noqa: E402


def build_daily_brief_from_authoring_contexts(
    contexts: list[AuthoringContext], date: str
) -> dict:
    """Reconstructs a daily_brief-shaped dict from a run's included
    AuthoringContext entries.

    Only collector_daily_brief-sourced contexts carry real
    commit_messages/diffstat/files_touched; collector_manifest-sourced
    contexts contribute commit_count only (no raw text) — expected, per
    ADR-0045, not an error. `mode` becomes "fact" iff at least one
    context contributes real commit message text; otherwise
    "idea_fallback" (mirrors Collector's own daily_brief.py mode
    heuristic in spirit — real text available vs. not — without
    reimplementing its exact diffstat/keyword thresholds, which this
    module has no basis to duplicate).

    commit_messages are the union of the INCLUDED contexts' own slices
    only (each context carries just its own repository's subjects — see
    collector.py's adapt_daily_brief()), so no excluded unit's message can
    appear here. Identical subject lines from different included repos are
    collapsed to one (behavior kept from when every unit carried the same
    brief-wide list; it no longer has any leak-related role).
    """
    total_diffstat = 0
    files_touched: list[str] = []
    commit_messages: list[str] = []
    per_repo = []

    for ctx in contexts:
        diffstat = ctx.diffstat or 0
        total_diffstat += diffstat
        files_touched.extend(ctx.files_touched)
        for msg in ctx.commit_messages:
            if msg not in commit_messages:
                commit_messages.append(msg)
        per_repo.append(
            {
                "name": ctx.repo,
                "commit_count": ctx.commit_count,
                "diffstat": diffstat,
                "files_touched": ctx.files_touched,
            }
        )

    mode = "fact" if commit_messages else "idea_fallback"

    return {
        "mode": mode,
        "date": date,
        "total_diffstat": total_diffstat,
        "files_touched": sorted(set(files_touched)),
        "commit_messages": commit_messages,
        "per_repo": per_repo,
    }
