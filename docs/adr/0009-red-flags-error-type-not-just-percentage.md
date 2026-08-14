# 0009 — Red flags classify error type, not just a raw percentage

## Status
Accepted. Not applied in practice.

## Context

A raw success percentage (e.g. "60% success") gives no diagnostic
information about why the other 40% failed.

## Decision

Red flags combine a percentage with an error category:
`no_claim` / `wrong_framing` / `bad_evidence` / `technical_failure`.

## Options considered

**A — Percentage only.** Rejected — a percentage without a mechanism is
false precision.

**B — Percentage plus category (chosen).**

## Consequences

Specified as a classification table in the pipeline design. Not applied
in practice — no release record shows this classification used on a
real run.

## Validation
Not applicable — not yet exercised.

## Reversal condition
None specified.

## Source
Unanimous agreement across three independent architectural reviews.
