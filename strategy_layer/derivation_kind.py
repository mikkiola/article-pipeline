"""Strategy Layer — derivation-kind rule table (SPEC.md extension,
"declarative derivation-kind classification for framing text").

Framing text is produced entirely by an automated process (never a
human typing free text) — either deterministic code, or Claude Code
acting per instruction during an interactive Strategy Layer session.
That same producing step must ALSO declare a `derivation_kind` label
alongside the framing text, at the moment it's created. This module is
the static, deterministic check — a dictionary lookup, not a model
call — of whether the declared kind is warranted by the framed unit's
`source_status_snapshot` (its `corroboration_status` as it was at the
moment framing was attached, plus how many source units the run
actually has).

This closes the gap found 2026-09-15: nothing previously re-evaluated
framing text against its source's actual verification status — a unit
ingested with corroboration_status=not_applicable could get framing
text attached that reads as an evaluative or causal claim, with
nothing distinguishing that from a bare, undisputed fact. The rule
table is checked at framing-attachment time, not by a second process
reading text back afterward.

**causal_claim is warranted only when source_corroboration_status ==
"corroborated"** — every other status (not_applicable, pending,
disputed, unsubstantiated) is unconditionally unwarranted. Corrected
2026-09-15 from an earlier version of this rule that named only
not_applicable/pending as unwarranted: disputed/unsubstantiated are,
if anything, weaker grounds for the strongest claim type in this
vocabulary, not stronger — a source external evidence actively
contradicts (disputed) is not a safer basis for a causal claim than
one merely awaiting evidence (pending). Owner-confirmed correction,
not a newly-invented extension.
"""

from __future__ import annotations

DERIVATION_KINDS = frozenset({"restatement", "aggregation", "evaluation", "causal_claim"})


def check_derivation_warranted(
    derivation_kind: str,
    source_corroboration_status: str,
    unit_count_in_run: int = 1,
    has_defined_aggregation_rule: bool = False,
) -> dict:
    """Returns {"warranted": bool, "reason": str | None}.

    `reason` is non-null iff `warranted` is False — explains why the
    declared derivation_kind was rejected, for direct use as the
    claim_treatment entry's `reason` field when a unit is refused on
    this basis.
    """
    if derivation_kind not in DERIVATION_KINDS:
        raise ValueError(
            f"unknown derivation_kind: {derivation_kind!r} — must be one of "
            f"{sorted(DERIVATION_KINDS)}"
        )

    if derivation_kind == "restatement":
        # Warranted against any source status — restatement adds nothing
        # beyond what the source record already states.
        return {"warranted": True, "reason": None}

    if derivation_kind == "aggregation":
        if unit_count_in_run <= 1:
            return {
                "warranted": False,
                "reason": (
                    "aggregation declared but only one source unit is "
                    "present in this run — a pattern claim across "
                    "multiple records requires multiple records"
                ),
            }
        return {"warranted": True, "reason": None}

    if derivation_kind == "evaluation":
        if source_corroboration_status == "corroborated":
            return {"warranted": True, "reason": None}
        if has_defined_aggregation_rule:
            return {"warranted": True, "reason": None}
        return {
            "warranted": False,
            "reason": (
                f"evaluation declared from corroboration_status="
                f"{source_corroboration_status!r} with no defined "
                f"aggregation rule — a normative/comparative judgment "
                f"needs either external corroboration or a reproducible "
                f"threshold to derive it from"
            ),
        }

    # derivation_kind == "causal_claim" — warranted only from corroborated;
    # every other status is unconditionally unwarranted (see module
    # docstring for why disputed/unsubstantiated are not exceptions).
    if source_corroboration_status != "corroborated":
        return {
            "warranted": False,
            "reason": (
                f"causal_claim is never warranted from corroboration_status="
                f"{source_corroboration_status!r}"
            ),
        }
    return {"warranted": True, "reason": None}
