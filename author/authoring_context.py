"""AuthoringContext — Author-facing data assembled post-classification,
directly from CanonicalUnit (ADR-0045: Post-Classification Authoring
Context).

Deliberately NOT part of the verdict/claim_treatments schema and
deliberately NOT imported by anything in strategy_layer/'s
classification logic (pre_filter.py, framing.py, write_verdict.py) —
confirmed zero such imports exist as of this module's introduction
(mandatory codebase-wide search, 2026-09-15). This is the structural
half of the Anti-Corruption-Layer boundary this whole migration exists
to enforce: classification code decides include/exclude and produces
framing from a unit's two-dimension status alone, and has no path
back to a unit's raw source-specific metadata (commit messages, file
lists, per-repo counts) — that data is only ever assembled here, by
this module, called from Author's side after classification is
already final.

build_authoring_contexts() reads already-computed claim_treatments
(a run's `final_classification`, not `pre_filter_classification` —
correctly accounts for any override) to decide which units qualify.
It does not re-run or duplicate any classification logic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "strategy_layer"))
from contract import CanonicalUnit  # noqa: E402


class AuthoringContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    framing: str | None
    source_type: str  # "collector_manifest" | "collector_daily_brief" (see ADR-0045's per-source_type whitelist)
    repo: str
    commit_count: int

    # Collector-daily (commit-message-bearing) units populate these;
    # Collector-weekly (manifest) units leave them at their defaults —
    # expected, not an error, per ADR-0045's design.
    diffstat: int | None = None
    files_touched: list[str] = []
    commit_messages: list[str] = []

    # Collector-weekly units populate this instead; Collector-daily
    # units leave it None.
    counts: dict[str, Any] | None = None


def build_authoring_contexts(
    units: list[CanonicalUnit], claim_treatments: list[dict]
) -> list[AuthoringContext]:
    """Builds one AuthoringContext per unit whose already-computed
    claim_treatment has `final_classification == "include"`.

    Matches units to treatments by claim_id (== unit.unit_id) — reads
    the classification result, never recomputes it.
    """
    treatment_by_id = {t["claim_id"]: t for t in claim_treatments}

    contexts = []
    for unit in units:
        treatment = treatment_by_id.get(unit.unit_id)
        if treatment is None or treatment["final_classification"] != "include":
            continue

        metadata = unit.metadata
        contexts.append(
            AuthoringContext(
                claim_id=unit.unit_id,
                framing=treatment.get("framing"),
                source_type=metadata["source_type"],
                repo=metadata["repo"],
                commit_count=metadata["commit_count"],
                diffstat=metadata.get("diffstat"),
                files_touched=metadata.get("files_touched", []),
                commit_messages=metadata.get("commit_messages", []),
                counts=metadata.get("counts"),
            )
        )
    return contexts
