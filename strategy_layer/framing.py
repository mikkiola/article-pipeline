"""Strategy Layer — Stage 2 framing pass + override mechanism (SPEC.md
Execution Model, Milestone M3).

Stage 2 is explicitly "Claude Code judgment (interactive)" per SPEC.md,
not a deterministic transform: `decide_framing()` documents that seam's
contract but has no mechanical implementation (see its own docstring) —
the actual framing decision is made interactively, one Claim at a time,
and the resulting string is passed directly to `build_claim_treatment()`.

`build_claim_treatment()` and `derive_overrides()` are the mechanical,
fully-testable half of Stage 2: assembling one claim_treatments entry
per SPEC.md's Data Model, enforcing the override mechanism's mandatory-
reason rule (Functional Requirement #5), and deriving the `overrides`
list from `claim_treatments` rather than maintaining it independently.

Out of scope for this module (later milestones, per SPEC.md): verdict
assembly and Immutable Lineage output writing (M4).
"""

from __future__ import annotations


def decide_framing(claim: dict, evidence: dict) -> str:
    """Stage 2 seam: given an included Claim (with its `context`) and its
    Evidence, produces the framing/voice string for that Claim — the
    actual judgment call ADR-0007 assigns to Strategy Layer.

    Deliberately unimplemented: SPEC.md is explicit that this decision is
    "Claude Code judgment (interactive)," not a deterministic transform
    reducible to string templates over Claim/Evidence fields — auto-
    generating framing text here would misrepresent a judgment call as a
    mechanical one. Production and test callers alike supply the already-
    decided framing string directly to `build_claim_treatment()` instead
    of calling this function expecting computed output.
    """
    raise NotImplementedError(
        "decide_framing() is Claude Code's interactive judgment seam "
        "(SPEC.md Execution Model, Stage 2) — it has no mechanical "
        "implementation. Decide the framing interactively and pass the "
        "resulting string to build_claim_treatment()'s `framing` argument."
    )


def build_claim_treatment(
    claim_id: str,
    pre_filter_classification: str,
    pre_filter_reason: str | None,
    final_classification: str | None = None,
    framing: str | None = None,
    override_reason: str | None = None,
) -> dict:
    """Builds one `claim_treatments` entry (SPEC.md Data Model).

    `final_classification` defaults to `pre_filter_classification` (no
    override). Enforces SPEC.md Functional Requirement #5's override
    mechanism: whenever the resulting `final_classification` differs from
    `pre_filter_classification`, `override_reason` is mandatory — not
    optional — regardless of which direction the override runs.

    `framing` is required (non-null) if and only if the resulting
    `final_classification` is `"include"`; it is discarded (forced to
    `None`) otherwise, so the invariant holds even if a caller mistakenly
    supplies one for an excluded Claim.

    `reason` on the returned entry is non-null whenever `final_
    classification == "exclude"` (a bare pre-filter exclude reuses
    `pre_filter_reason`, matching M1's convention) or whenever an
    override occurred in either direction (a fresh `override_reason` is
    used instead, even if the override lands on `"include"`) — a bare
    pre-filter include with no override carries no reason.
    """
    if final_classification is None:
        final_classification = pre_filter_classification

    is_override = final_classification != pre_filter_classification

    if is_override and not override_reason:
        raise ValueError(
            f"{claim_id}: override from '{pre_filter_classification}' to "
            f"'{final_classification}' requires a non-null, non-empty reason"
        )

    if final_classification == "include":
        if not framing:
            raise ValueError(
                f"{claim_id}: final_classification is 'include' but no "
                f"framing was supplied"
            )
    else:
        framing = None

    if is_override:
        reason = override_reason
    elif final_classification == "exclude":
        reason = pre_filter_reason
    else:
        reason = None

    return {
        "claim_id": claim_id,
        "pre_filter_classification": pre_filter_classification,
        "final_classification": final_classification,
        "framing": framing,
        "reason": reason,
    }


def derive_overrides(claim_treatments: list[dict]) -> list[dict]:
    """Derives SPEC.md's `overrides` list from `claim_treatments`.

    Not independently maintained — SPEC.md's Data Model design note: this
    list is "always recomputable from claim_treatments and is not
    independently authoritative," kept only for the visibility of
    spotting an override pattern later without diffing every entry.
    """
    return [
        {
            "claim_id": treatment["claim_id"],
            "pre_filter_classification": treatment["pre_filter_classification"],
            "final_classification": treatment["final_classification"],
            "reason": treatment["reason"],
        }
        for treatment in claim_treatments
        if treatment["final_classification"] != treatment["pre_filter_classification"]
    ]
