# 0008 — Configurable confidence threshold instead of full human-in-the-loop

## Status
Accepted. Implementation status unclear — see conflict note below.

## Context

A fully manual human-in-the-loop review was rejected as too slow for a
solo-developer budget, but a binary "confident / not confident" flag was
judged too coarse, and a full auto-calibrating RL system risked quietly
reconstructing the human-in-the-loop pattern it was meant to avoid.

## Decision

A configurable numeric threshold, starting low (0.5 as an initial,
non-binding value — explicitly not confirmed as final at time of
writing), raised manually over time as trust in the system's output
grows.

## Options considered

**A — Binary confident/not-confident flag.** Rejected as too coarse.

**B — Configurable numeric threshold (chosen).**

**C — Full auto-calibrating RL system.** Rejected — excessive for the
current stage, risks silently building a human-in-the-loop system in a
different shape.

## Consequences

Specified as a Claim Extraction heuristic. **Known conflict, not yet
resolved as of this writing:** the actual 2026-08-11 Claim Extraction
pilot session used Claude Code's interactive assessment rather than an
automatic numeric threshold (see 0020). Whether these are the same
mechanism described two different ways, or two different layers, has
not been technically verified.

## Validation
Unverified. No release record describes the confidence mechanism as
implemented and running.

## Reversal condition
None specified — the starting value (0.5) was explicitly marked
"example, not confirmed" at the time of the decision and may need
explicit confirmation before being treated as final.

## Source
Convergent input from three independent architectural reviews, plus an
owner clarification that the starting value is not yet locked.
