# 0003 — Provocative packaging is allowed; content accuracy is not negotiable

## Status
Accepted.

## Context

Article Pipeline needs a clear boundary between how an article is
packaged (headline, framing, hook) and what it claims as fact.

## Decision

Packaging may be sharp or provocative. Factual content must always be
accurate — packaging never trades against accuracy.

## Options considered

**A — Both packaging and content stay conservative.** Rejected —
unnecessarily limits reach without a factual-accuracy justification.

**B — Trade accuracy for reach when useful (chosen: rejected).**
Rejected explicitly — accuracy is treated as non-negotiable regardless
of packaging strategy.

**Chosen: packaging is free to be sharp; content accuracy is fixed.**

## Consequences

Locked in as Quality Gate criterion (c) in the pipeline design — must
never soften criteria (a)/(b), which cover factual accuracy directly.

## Validation
Unverified — Quality Gate is not implemented; the criterion has not been
tested against a real artifact.

## Reversal condition
None specified.

## Source
Direct owner answer to a clarifying question. Re-classified later from
"architectural principle" to "current adaptive-layer value" under 0004 —
the principle itself did not change, only its position in the hierarchy.
