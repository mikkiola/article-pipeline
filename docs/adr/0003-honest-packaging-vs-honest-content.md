# 0003 — Provocative packaging is allowed; content accuracy is not negotiable

## Status
ACTIVE. Later re-classified from "architectural principle" to "current
adaptive-layer value" under 0004 — the principle itself did not change,
only its position in the hierarchy.

## Decision
Packaging (headline, framing, hook) may be sharp or provocative. Factual
content must always be accurate. Packaging never trades against
accuracy.

## Options
A — both packaging and content stay conservative. B — trade accuracy for
reach when useful. C — packaging free to be sharp, content accuracy
fixed (chosen).

## Chosen
C.

## Why
Reach without a factual-accuracy floor risks the project's core Evidence
invariant (see 0004) — the two are architecturally different concerns,
and conflating them would let engagement pressure quietly erode
accuracy over time. Keeping them independent means packaging can be
tuned freely per platform without ever touching the accuracy question.

## Constraints
Locked in as Quality Gate criterion (c) — must never soften criteria
(a)/(b), which cover factual accuracy directly.

## Rejected
A — unnecessarily limits reach without a factual-accuracy justification.
B — explicitly rejected: accuracy is non-negotiable regardless of
packaging strategy.

## Consequences
Quality Gate design now carries three criteria instead of two, with an
explicit non-softening rule between them.

## Validation
Unverified — Quality Gate is not implemented; the criterion has not been
tested against a real artifact.

## Reversal condition
None specified.

## Source
Direct owner answer to a clarifying question.
