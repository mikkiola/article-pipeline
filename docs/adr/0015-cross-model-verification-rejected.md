# 0015 — cross-model-verification rejected on principle, not budget

## Status
ACTIVE. `/verify` and `drift-control.md` implemented and confirmed
working in production; `cross-model-verification.md` deliberately not
installed.

## Decision
Install only `/verify` and `drift-control.md`. Do not install
`cross-model-verification.md`.

## Options
A — install cross-model-verification.md (Claude-vs-Codex review cycle).
B — install only `/verify` + `drift-control.md` (chosen).

## Chosen
B.

## Why
An LLM-vs-LLM dispute with no external human arbiter is a source of
wasted effort in itself, independent of budget — two probabilistic
outputs agreeing with each other is not the same as independent
verification. This reasoning was explicitly upgraded from "no budget for
a second model" to a standing architectural principle, consistent with a
prior decision made in a separate project under the same reasoning.

## Constraints
Any future re-introduction of cross-model review must involve genuine
independence (different goals, different inputs, different assumptions
— not just a second LLM call with the same prompt) to be treated as
real verification rather than another instance of the rejected pattern.

## Rejected
A — an LLM-vs-LLM dispute with no external human arbiter does not
produce genuine independent verification.

## Consequences
Confirmed working for Evidence Package (2026-08-13) via the
`CHECKPOINT.md` pattern. Known gap: in the earlier Claim Extraction
session (2026-08-11), these same tools were installed but not actually
invoked — discovered only after the fact. The gap was closed by
introducing a mandatory `CHECKPOINT.md` pattern requirement, which then
worked as intended for Evidence Package.

## Validation
Partially confirmed: worked as designed for Evidence Package
(`drift-control` showed an honest combined score of 0.10 on milestone
M2); did not fire at all for Claim Extraction — not a failure of the
tool, it was simply never invoked.

## Reversal condition
None specified.

## Source
Explicit owner agreement; reasoning re-classified from budget constraint
to standing principle.
