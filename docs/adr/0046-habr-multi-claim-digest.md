---
id: ADR-0046
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0046: Habr Multi-Claim Digest

## Status

Accepted.

## Context & Constraints

`SPEC.md`'s original design for the Strategy-Layer-fed Habr path
(Migration Sequence, M5) deliberately scoped `habr_verdict_to_story.py`
to exactly one included claim per run — "multi-claim synthesis is
explicitly deferred," a decision made during the `/spec` interview
with no real data yet available to test it against.

M5's real end-to-end run
(`strategy_layer/run_habr_pilot.py`, against real, current
`collector/data/manifest_2026-09-12.json`) confirmed this assumption
fails against realistic data: the run produced 5 included claims (5
repos with `integrity_status=valid` and a pre-filter `include`
classification, per the two-dimension model), and
`build_canonical_story()` correctly raised
`MultiClaimNotSupportedError` rather than fabricating a story from a
single arbitrarily-chosen claim. The literal run output (verdict
`strategy_layer/output/verdict_20260916T125419.json`) shows this is
not an edge case — it is what a typical week's real Collector data
looks like. Under the single-claim design, Habr publication does not
work against real data at all.

## Decision

Replace the single-claim `CanonicalStory`-based design with a
multi-claim digest: one small section per included claim (repo +
already-vetted framing text), rendered under one shared Russian title,
structural juxtaposition rather than narrative synthesis — no
cross-claim evaluative or aggregative sentence is added (no "activity
was strong across the workspace this week"), so nothing new is being
claimed beyond what each individual claim's own already-warranted
`derivation_kind="restatement"` framing already asserts.

A per-claim `looks_russian()` check runs for each context; a claim
that fails is excluded from the digest with a clearly logged reason,
not silently dropped — mirrors `pre_filter.check_gate_condition()`'s
own existing "zero survivors triggers refusal, partial survival
doesn't" pattern, applied at this later stage rather than invented
fresh. The whole digest refuses only if zero claims survive the
check.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| **A. Top-1-claim-only compromise** — publish using only the highest-activity repo, silently drop the rest. | Rejected, explicitly, per owner instruction. Doesn't represent the actual week — a Habr post claiming to report "this week's engineering activity" while silently omitting 4 of 5 real active repos is exactly the kind of packaging-overclaims-accuracy gap `docs/adr/0003-honest-packaging-vs-honest-content.md`'s non-negotiable floor already forbids elsewhere in this pipeline, and the same "explicit refusal over silent mangling" principle this session has applied repeatedly (the `>1`-included-claim refusal this ADR itself is resolving, the `derivation_kind` unwarranted-forces-exclude path) argues against it here too. |
| **B. LLM-synthesized single narrative across all claims.** | Rejected. Every current Habr framing string is a plain restatement of one repo's raw counts — there is no narrative content to synthesize, only facts to present together. Introduces a new cost and failure surface (an LLM call, Habr's pipeline has never had one — ADR-0043's "first, inspectable, hand-editable prototype" design) for a problem structural formatting already solves. The prior art both academic multi-document-summarization practice and practical tools (Gitmore, gitlog-weekly) point to for "multiple recent items -> one periodic post" is aggregation/listing, not narrative synthesis. |
| **C. Chosen — structural multi-section digest, no LLM, per-claim language-check with partial-exclusion.** | Represents the real week honestly (all real, valid claims included, not one cherry-picked); costs nothing new (no LLM, no new external dependency); reuses `AuthoringContext` and the existing `derivation_kind`/`looks_russian()` mechanisms unchanged rather than inventing new gates. |

**Scope note, recorded as part of this decision's own rationale, not
just an implementation detail:** the owner's explicit standing
instruction for this decision was to prioritize a correct, complete
result over minimizing effort should the two diverge, and to default
to real synthesis over a partial/single-claim compromise if the effort
were roughly comparable either way. In this case there was no actual
tension to resolve — the correct design (Option C) is also the
smaller, more contained one (Habr-side only, no `AuthoringContext`
changes, no LinkedIn-path ripple) — but the instruction is recorded
here because it is this decision's own stated rationale, not
incidental.

## Consequences

- `habr_verdict_to_story.py` no longer imports or produces
  `CanonicalStory` (`story_builder.py`'s dataclass) — replaced by two
  new, small Pydantic models scoped to this file:
  `HabrDigestSection` (one per included, language-check-passing claim)
  and `HabrDigest` (title + `sections: list[HabrDigestSection]`).
  `story_builder.py`, `channel_author.py`, `generate_drafts.py`, and
  `test_pipeline.py` are unaffected — none of them import from
  `habr_verdict_to_story.py`.
- `AuthoringContext` (`author/authoring_context.py`, ADR-0045) is
  unchanged — this decision confirms, rather than revises, that ADR's
  boundary: the digest is still built post-classification, directly
  from a list of already-produced `AuthoringContext` entries, never
  touching `strategy_layer/`'s classification logic.
- `habr_weekly_author.py` gains a new rendering function for the
  digest shape, replacing `render_habr_draft()`'s single-`CanonicalStory`
  signature.
- `MultiClaimNotSupportedError` (introduced in the prior M5 task) is
  removed — multi-claim is now the supported, expected case, not a
  refused one.

## Confirmation & Revisit

Validated by construction (new TDD test suite) and by a real
end-to-end run against the same `manifest_2026-09-12.json` data that
surfaced this gap, confirming all real included claims are represented
in the output, not a silently truncated subset. Revisit if a future
real run shows the "no LLM, pure structural listing" design produces
genuinely unreadable output at higher claim counts (e.g. 20+ active
repos in one week) — that would be a new, data-driven trigger for
revisiting this decision, not assumed here.

## Source

M5 continuation session, 2026-09-16, following `strategy_layer/
run_habr_pilot.py`'s real run against `manifest_2026-09-12.json`
(5 included claims, `verdict_20260916T125419.json`) and the owner's
explicit decision to extend multi-claim support this sprint rather
than accept non-functional Habr publication against real data.
