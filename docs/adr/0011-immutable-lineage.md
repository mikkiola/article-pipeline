---
id: ADR-0011
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0011 — Immutable Lineage: published artifacts are never overwritten

## Status

ACTIVE. Most reliably implemented invariant in the project — confirmed
twice on real production data.

## Context & Constraints

Without an append-only history, the Experiment Log becomes meaningless —
an observation tied to text that no longer exists in its original form
provides no reliable basis for comparing what changed. Editing in place
would silently destroy the ability to trace what was actually evaluated
at the time of any past decision.

A repeat write with the same run ID must fail loudly (not silently
overwrite). File modification time on an existing artifact must never
change after its first write.

## Decision

After publication or fixation, an artifact (Claim, Evidence, Canonical
Article) is never overwritten. A new version is a new file with a link
back to the previous one.

## Alternatives & Rationale

A — edit in place over the published version. B — strict append-only
(chosen).

B.

A — destroys traceability of what was actually evaluated historically.

## Consequences

Implemented and confirmed on real data twice: Claim Extraction
(2026-08-11, `pilot_run_*.json`) and Evidence Package (2026-08-13,
`evidence_run_20260813T114717.json`). A deliberate repeat write with the
same run ID raises `FileExistsError`; file modification time does not
change.

## Confirmation & Revisit

Confirmed on real production runs, not only on stubs, in both components
listed above.

None specified.

**Source.** Unanimous support across three independent architectural reviews, plus
practical confirmation in production.
