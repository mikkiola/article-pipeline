---
id: ADR-0008
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0008 — Configurable confidence threshold instead of full human-in-the-loop

## Status

ACTIVE. Implementation status unclear — possible overlap with 0020, not
yet technically verified.

## Context & Constraints

A binary flag was judged too coarse to be useful, while a full
auto-calibrating RL system risked quietly reconstructing a full
human-in-the-loop system in a different shape — exactly the pattern this
decision was meant to avoid. A configurable threshold gives graded
control without either extreme.

Threshold must remain owner-adjustable, not hardcoded. Starting value
(0.5) is explicitly not final.

## Decision

A configurable numeric threshold, starting low (0.5 — explicitly marked
"example, not confirmed" at the time of the decision), raised manually
over time as trust in the system's output grows.

## Alternatives & Rationale

A — binary confident/not-confident flag. B — configurable numeric
threshold (chosen). C — full auto-calibrating RL system.

B.

A — too coarse. C — excessive for the current stage, risks silently
building a human-in-the-loop system in a different shape.

## Consequences

Specified as a Claim Extraction heuristic. Known open conflict: the
actual 2026-08-11 Claim Extraction pilot session used Claude Code's
interactive assessment rather than an automatic numeric threshold (see
0020). Whether these are the same mechanism described two different
ways, or two different layers, has not been technically verified.

## Confirmation & Revisit

Unverified. No release record describes the confidence mechanism as
implemented and running.

None specified — the starting value (0.5) was explicitly marked
"example, not confirmed" and may need explicit confirmation before being
treated as final.

**Source.** Convergent input from three independent architectural reviews, plus an
owner clarification that the starting value is not yet locked.
