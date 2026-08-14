# 0015 — cross-model-verification rejected on principle, not budget

## Status
Accepted. `/verify` and `drift-control.md` implemented and confirmed
working in production; `cross-model-verification.md` deliberately not
installed.

## Context

Grill Me / Dual Review (the project's normal peer-check process) were
temporarily suspended due to budget constraints (Sonnet only, no second
reviewer model). A replacement was needed.

## Decision

Install only `/verify` and `drift-control.md`. Do not install
`cross-model-verification.md`.

## Options considered

**A — Install cross-model-verification.md (Claude-vs-Codex cycle).**
Rejected — an LLM-vs-LLM dispute with no external human arbiter is a
source of wasted effort in itself, independent of budget. This
reasoning was later upgraded from "no budget for Codex" to a standing
architectural principle, consistent with a prior decision in a separate
project.

**B — Install only `/verify` + `drift-control.md` (chosen).**

## Consequences

Confirmed working for Evidence Package (2026-08-13) via the
`CHECKPOINT.md` pattern (see 0028's related note on the same pattern).
**Known gap**: in the earlier Claim Extraction session (2026-08-11),
these same tools were installed but not actually invoked — discovered
only after the fact. The gap was closed by introducing a mandatory
`CHECKPOINT.md` pattern requirement, which then worked as intended for
Evidence Package.

## Validation
Partially confirmed: worked as designed for Evidence Package
(`drift-control` showed an honest combined score of 0.10 on milestone
M2); did not fire at all for Claim Extraction (not a failure of the
tool — it was simply never invoked).

## Reversal condition
None specified.

## Source
Explicit owner agreement; reasoning re-classified from budget constraint
to standing principle.
