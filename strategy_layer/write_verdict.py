"""Verdict assembly + Immutable Lineage output writer (SPEC.md Data
Model, Non-Functional Requirement #3, Milestone M4).

Assembles Strategy Layer's one-verdict-per-run object — its contract to
Author, per docs/adr/0007-strategy-layer-separate-from-platform-
adapter.md — from M2's gate-check result and M3's claim_treatments
entries. `overrides` is derived from `claim_treatments` via
framing.derive_overrides() internally, not accepted as a separate
argument, so build_verdict() can never be called with an inconsistent
(claim_treatments, overrides) pair.

Output writer matches evidence_package/write_evidence.py's
write_outputs() convention: never overwrites a previous run — a run_id
collision raises FileExistsError instead of silently overwriting.
Strategy Layer's Data Model is a single verdict object per run (not the
run+log pair evidence_package writes), so this writes one file, adapting
evidence_package's two-file existence-check loop to the one file this
schema actually has.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import framing

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def build_verdict(run_id: str, gate_result: dict, claim_treatments: list[dict]) -> dict:
    """Assembles one verdict object per SPEC.md's Data Model.

    `gate_result` is M2's check_all_claims_unverifiable_gate() output
    (carries both the top-level `status` and the `gates` object).
    `overrides` is derived from `claim_treatments`, not accepted as an
    argument — the two can never drift out of sync.
    """
    return {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "status": gate_result["status"],
        "gates": gate_result["gates"],
        "claim_treatments": claim_treatments,
        "overrides": framing.derive_overrides(claim_treatments),
    }


def write_outputs(run_id: str, verdict: dict) -> str:
    """Writes verdict_<run_id>.json (Immutable Lineage).

    Never overwrites a previous run: a run_id collision raises
    FileExistsError instead of silently overwriting — same pattern as
    evidence_package/write_evidence.py's write_outputs().
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    verdict_path = os.path.join(OUTPUT_DIR, f"verdict_{run_id}.json")

    if os.path.exists(verdict_path):
        raise FileExistsError(
            f"{verdict_path} already exists — Immutable Lineage forbids "
            f"overwriting a previous run."
        )

    with open(verdict_path, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)

    return verdict_path
