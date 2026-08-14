# 0011 — Immutable Lineage: published artifacts are never overwritten

## Status
Accepted. Implemented and confirmed twice in production.

## Context

Without an append-only history, the Experiment Log becomes meaningless
— an observation tied to text that no longer exists in its original
form provides no reliable basis for comparison.

## Decision

After publication or fixation, an artifact (Claim, Evidence, Canonical
Article) is never overwritten. A new version is a new file with a link
back to the previous one.

## Options considered

**A — Edit in place over the published version.** Rejected — destroys
the ability to trace what was actually evaluated at the time of any
past decision.

**B — Strict append-only (chosen).**

## Consequences

Implemented and confirmed on real data twice: Claim Extraction
(2026-08-11, `pilot_run_*.json`) and Evidence Package (2026-08-13,
`evidence_run_20260813T114717.json`). A deliberate repeat write with the
same run ID raises `FileExistsError`; file modification time does not
change.

## Validation
Confirmed on real production runs, not only on stubs, in both
components listed above.

## Reversal condition
None specified.

## Source
Unanimous support across three independent architectural reviews, plus
practical confirmation in production.
