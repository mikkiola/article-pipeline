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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derivation_kind as derivation_kind_module  # noqa: E402


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

    Framing text is never human-typed — it is produced entirely by this
    automated seam (Claude Code acting per instruction during an
    interactive Strategy Layer session, or future deterministic code).
    Two requirements on whoever produces it, per SPEC.md's "declarative
    derivation-kind classification for framing text" extension
    (2026-09-15) — both are instructions to the producer, not runtime
    checks on free text after the fact:

    1. **Habr-bound framing must be written in Russian.** Confirmed this
       session: no mechanism anywhere in this pipeline previously
       constrained framing's output language — the one real example on
       disk (`strategy_layer/output/verdict_20260828T211939.json`) is
       English, purely because that's the language the interactive
       session producing it happened to use. `strategy_layer/
       language_check.py`'s `looks_russian()` is an optional, explicitly
       secondary safety net (a crude Cyrillic-ratio heuristic) the new
       Habr entry point (SPEC.md's M5, not yet built) may call before
       accepting a framing string — it does not replace this instruction.
    2. **Every framing string must declare a `derivation_kind`**
       (`"restatement" | "aggregation" | "evaluation" | "causal_claim"`,
       see `strategy_layer/derivation_kind.py`) alongside the text
       itself, plus the unit's `source_status_snapshot` (its
       `integrity_status`/`corroboration_status` as they were at framing
       time, not a live reference) — both required for
       `derivation_kind.check_derivation_warranted()` to run at
       framing-attachment time.
    """
    raise NotImplementedError(
        "decide_framing() is Claude Code's interactive judgment seam "
        "(SPEC.md Execution Model, Stage 2) — it has no mechanical "
        "implementation. Decide the framing interactively and pass the "
        "resulting string to build_claim_treatment()'s `framing` argument. "
        "Habr-bound framing must be in Russian; every framing string must "
        "declare a derivation_kind and source_status_snapshot — see this "
        "function's docstring and strategy_layer/derivation_kind.py."
    )


def build_claim_treatment(
    claim_id: str,
    pre_filter_classification: str,
    pre_filter_reason: str | None,
    final_classification: str | None = None,
    framing: str | None = None,
    override_reason: str | None = None,
    derivation_kind: str | None = None,
    source_status_snapshot: dict | None = None,
    unit_count_in_run: int = 1,
    has_defined_aggregation_rule: bool = False,
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

    **derivation_kind / source_status_snapshot** (SPEC.md's declarative
    derivation-kind extension, 2026-09-15, Milestone M3 Part 2):
    optional, opt-in — when a Claim is actually included (framing
    attempted), a caller may additionally declare `derivation_kind`
    (one of `strategy_layer.derivation_kind.DERIVATION_KINDS`) alongside
    a `source_status_snapshot` (`{"integrity_status": ...,
    "corroboration_status": ...}`, the unit's status AS IT WAS at framing
    time — a snapshot, not a live reference). When supplied,
    `derivation_kind.check_derivation_warranted()` runs at this moment;
    an `unwarranted` result forces `final_classification` back to
    `"exclude"` and discards `framing` — the unit is refused, not
    silently published as if the declared kind were warranted.
    `derivation_kind`/`source_status_snapshot` are only present as keys
    on the returned dict when actually supplied and framing was
    attempted — omitted entirely (not present as `None` keys) when not
    supplied, so every pre-existing caller that doesn't use this
    mechanism gets the exact same dict shape as before.
    """
    if final_classification is None:
        final_classification = pre_filter_classification

    is_override = final_classification != pre_filter_classification

    if is_override and not override_reason:
        raise ValueError(
            f"{claim_id}: override from '{pre_filter_classification}' to "
            f"'{final_classification}' requires a non-null, non-empty reason"
        )

    framing_attempted = final_classification == "include"

    if framing_attempted:
        if not framing:
            raise ValueError(
                f"{claim_id}: final_classification is 'include' but no "
                f"framing was supplied"
            )
    else:
        framing = None
        derivation_kind = None
        source_status_snapshot = None

    derivation_unwarranted_reason = None
    if framing_attempted and derivation_kind is not None:
        if source_status_snapshot is None:
            raise ValueError(
                f"{claim_id}: derivation_kind supplied without "
                f"source_status_snapshot"
            )
        check = derivation_kind_module.check_derivation_warranted(
            derivation_kind,
            source_status_snapshot["corroboration_status"],
            unit_count_in_run=unit_count_in_run,
            has_defined_aggregation_rule=has_defined_aggregation_rule,
        )
        if not check["warranted"]:
            final_classification = "exclude"
            framing = None
            derivation_unwarranted_reason = check["reason"]

    if derivation_unwarranted_reason is not None:
        reason = derivation_unwarranted_reason
    elif is_override:
        reason = override_reason
    elif final_classification == "exclude":
        reason = pre_filter_reason
    else:
        reason = None

    result = {
        "claim_id": claim_id,
        "pre_filter_classification": pre_filter_classification,
        "final_classification": final_classification,
        "framing": framing,
        "reason": reason,
    }
    if derivation_kind is not None:
        result["derivation_kind"] = derivation_kind
        result["source_status_snapshot"] = source_status_snapshot

    return result


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
