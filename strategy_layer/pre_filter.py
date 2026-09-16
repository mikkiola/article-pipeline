"""Strategy Layer — Stage 1 deterministic pre-filter (two-dimension
model, SPEC.md's source-independence extension, Milestone M2).

Classifies each CanonicalUnit from `integrity_status` +
`corroboration_status` together, per SPEC.md's 6-row matrix — replaces
the single-status verified/disputed/unverifiable/pending table this
module used before 2026-09-15.

No join happens here any more. The old join_claims_and_evidence()
(joining Claim + Evidence 1:1 on claim_id, refusing the whole run on a
missing match or null context) is removed: each source adapter is now
responsible for producing one complete, valid CanonicalUnit per
meaningful raw record — Pydantic's own construction-time validation
(contract.py's extra="forbid" + model_validator) is the input-
validation gate, at the ACL boundary, not inside this module.

Also computes SPEC.md's redefined v1 gate condition (Milestone M2):
`status="gated"` when zero units in the run classify "include" —
generalizes the old "all Evidence unverifiable" condition to "nothing
survived the filter," working identically for a Collector-only,
Brain-only, or mixed run.

Out of scope for this module (later milestones, per SPEC.md): Claude
Code's framing pass, the derivation_kind rule table, and override
mechanism (M3); verdict assembly and Immutable Lineage output writing
(M4).
"""

from __future__ import annotations

from contract import CanonicalUnit

_EXCLUDE_REASON = {
    "disputed": (
        "Disputed evidence — per docs/adr/0003-honest-packaging-vs-honest-"
        "content.md's non-negotiable accuracy floor (\"packaging never "
        "trades against accuracy\"), a contested fact is not an "
        "established one by default."
    ),
    "unsubstantiated": "No corroborating evidence found; accuracy not established.",
    "pending": "Not yet resolved; do not publish prematurely.",
}


def classify_unit(unit: CanonicalUnit) -> dict:
    """Computes one unit's pre_filter_classification per SPEC.md's
    two-dimension matrix:

    | integrity_status | corroboration_status | classification |
    |---|---|---|
    | invalid | (any) | exclude — integrity is a hard floor, checked first |
    | valid | corroborated | include |
    | valid | not_applicable | include |
    | valid | disputed / unsubstantiated / pending | exclude |

    Output key is `claim_id` (not `unit_id`) to keep framing.py/
    write_verdict.py's existing field names unchanged — a deliberate
    naming choice recorded in SPEC.md's Data Model notes.
    """
    if unit.integrity_status == "invalid":
        return {
            "claim_id": unit.unit_id,
            "pre_filter_classification": "exclude",
            "reason": (
                f"integrity_status=invalid ({unit.integrity_check_method}) "
                f"— an inauthentic/unprovenanced record can never be "
                f"included, regardless of corroboration_status"
            ),
        }

    # integrity_status == "valid"
    if unit.corroboration_status in ("corroborated", "not_applicable"):
        return {
            "claim_id": unit.unit_id,
            "pre_filter_classification": "include",
            "reason": None,
        }

    return {
        "claim_id": unit.unit_id,
        "pre_filter_classification": "exclude",
        "reason": _EXCLUDE_REASON[unit.corroboration_status],
    }


def run_pre_filter(units: list[CanonicalUnit]) -> list[dict]:
    """Classifies every unit in a run (Stage 1, full pass)."""
    return [classify_unit(unit) for unit in units]


def check_gate_condition(pre_filter_results: list[dict]) -> dict:
    """Evaluates SPEC.md's redefined v1 gate condition (Milestone M2)
    over a run's pre-filter results.

    Fires — `status: "gated"`, `gates.zero_included_units: True` — iff
    the run is non-empty and every result's `pre_filter_classification`
    is "exclude". An empty run (zero units at all) does not fire the
    gate — preserves the original gate's defensive convention: there's
    nothing to gate, not "everything got excluded."
    """
    included_count = sum(
        1 for r in pre_filter_results if r["pre_filter_classification"] == "include"
    )
    zero_included = bool(pre_filter_results) and included_count == 0
    return {
        "status": "gated" if zero_included else "normal",
        "gates": {"zero_included_units": zero_included},
    }
