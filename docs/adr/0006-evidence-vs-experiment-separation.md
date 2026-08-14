# 0006 — Evidence and Experiment are separate data layers

## Status
Accepted. Evidence side implemented and validated on real data;
Experiment side not implemented.

## Context

"Is this claim true" (Evidence) and "did this framing work on this
audience" (Experiment) are different questions and were at risk of being
collapsed into one structure with a single confidence field.

## Decision

Evidence (truth of a claim, proven by source) and Experiment
(effectiveness of an intervention) are kept as separate data structures,
never merged.

## Options considered

**A — Single structure with one confidence field.** Rejected — conflates
two different kinds of uncertainty.

**B — Separate structures (chosen).**

## Consequences

Evidence Package was implemented and validated on 2026-08-13 (5 live
Claims run through Linkup, final result 5/5 unverifiable, manually
verified against full source text, not just snippets). This is the only
decision in the full set with a complete cycle from intent through to
real-data validation. Experiment Log (the Experiment half) remains
unimplemented.

## Validation
Confirmed. Real pipeline run, 5 Claims processed, verdicts manually
checked against full source pages by the architect, not snippets alone.

## Reversal condition
None specified.

## Source
Convergent input from three independent architectural reviews, plus a
real production run confirming the Evidence half.
