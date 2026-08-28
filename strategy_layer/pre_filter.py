"""Strategy Layer — Stage 1 deterministic pre-filter (SPEC.md Execution
Model, Milestone M1).

Joins a run's Claims and Evidence records 1:1 on claim_id and computes
each pair's pre_filter_classification from Evidence's `status` field,
per SPEC.md's four-row table. Also enforces SPEC.md's Missing Input
Data contract: a Claim with no matching Evidence record, or no
non-null `context` field, means Strategy Layer is being run out of
order — this module refuses to proceed for the whole run rather than
silently skipping the affected Claim.

Out of scope for this module (later milestones, per SPEC.md): the v1
gate check (M2), Claude Code's framing pass and override mechanism
(M3), verdict assembly and Immutable Lineage output writing (M4).
"""

from __future__ import annotations

PRE_FILTER_CLASSIFICATION = {
    "verified": "include",
    "disputed": "exclude",
    "unverifiable": "exclude",
    "pending": "exclude",
}

PRE_FILTER_REASON = {
    "verified": None,
    "disputed": (
        "Disputed evidence — per docs/adr/0003-honest-packaging-vs-honest-"
        "content.md's non-negotiable accuracy floor (\"packaging never "
        "trades against accuracy\"), a contested fact is not an "
        "established one by default."
    ),
    "unverifiable": "No evidence found; accuracy not established.",
    "pending": "Not yet resolved; do not publish prematurely.",
}


def join_claims_and_evidence(
    claims: list[dict], evidence_records: list[dict]
) -> list[tuple[dict, dict]]:
    """Joins Claims and Evidence records 1:1 on claim_id.

    Raises ValueError, naming the specific claim_id and the missing
    field or record, when a Claim has no matching Evidence record or
    no non-null `context` field. Per SPEC.md's Missing Input Data
    section, this is a run-level pipeline-ordering error: the whole
    run refuses to proceed, not just the affected Claim.
    """
    evidence_by_claim_id = {record["claim_id"]: record for record in evidence_records}

    pairs = []
    for claim in claims:
        claim_id = claim["claim_id"]

        if claim.get("context") is None:
            raise ValueError(
                f"{claim_id}: missing 'context' field — Strategy Layer is "
                f"being run out of order, before the Context layer has "
                f"processed this Claim."
            )

        evidence = evidence_by_claim_id.get(claim_id)
        if evidence is None:
            raise ValueError(
                f"{claim_id}: no matching Evidence record — Strategy Layer "
                f"is being run out of order, before Evidence Package has "
                f"processed this Claim."
            )

        pairs.append((claim, evidence))

    return pairs


def classify_pair(claim: dict, evidence: dict) -> dict:
    """Computes one pair's pre_filter_classification per SPEC.md's table."""
    status = evidence["status"]
    return {
        "claim_id": claim["claim_id"],
        "pre_filter_classification": PRE_FILTER_CLASSIFICATION[status],
        "reason": PRE_FILTER_REASON[status],
    }


def run_pre_filter(claims: list[dict], evidence_records: list[dict]) -> list[dict]:
    """Joins Claims/Evidence and classifies every pair (Stage 1, full pass)."""
    pairs = join_claims_and_evidence(claims, evidence_records)
    return [classify_pair(claim, evidence) for claim, evidence in pairs]
