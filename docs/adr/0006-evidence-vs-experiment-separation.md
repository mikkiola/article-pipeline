# 0006 — Evidence and Experiment are separate data layers

## Status
ACTIVE. Most mature decision in the full set — the only one with a
complete cycle through real-data validation on both its Evidence half.

## Decision
Evidence (truth of a claim, proven by source) and Experiment
(effectiveness of an intervention on a specific audience) are kept as
separate data structures, never merged into one.

## Options
A — single structure with one confidence field. B — separate structures
(chosen).

## Chosen
B.

## Why
"Is this claim true" and "did this framing work on this audience" are
different questions with different failure modes — a claim can be true
and land badly, or false and land well. Collapsing them into one
confidence number would hide which kind of failure actually happened,
making the system unable to learn the right lesson from a bad outcome.

## Constraints
Evidence Package and Experiment Log must never share a single confidence
field or merged record type, even where it would be more convenient
short-term.

## Rejected
A — conflates two different kinds of uncertainty into one number.

## Consequences
Evidence Package was implemented and validated on 2026-08-13 (5 live
Claims run through Linkup, final result 5/5 unverifiable, manually
verified against full source text, not just snippets). Experiment Log
(the Experiment half) remains unimplemented.

## Validation
Confirmed. Real pipeline run, 5 Claims processed, verdicts manually
checked against full source pages by the architect, not snippets alone.

## Reversal condition
None specified.

## Source
Convergent input from three independent architectural reviews, plus a
real production run confirming the Evidence half.
