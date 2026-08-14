# 0009 — Red flags classify error type, not just a raw percentage

## Status
ACTIVE, not applied in practice.

## Decision
Red flags combine a percentage with an error category:
`no_claim` / `wrong_framing` / `bad_evidence` / `technical_failure`.

## Options
A — percentage only. B — percentage plus category (chosen).

## Chosen
B.

## Why
A raw success percentage (e.g. "60% success") gives no information about
why the other 40% failed — it invites false confidence in a diagnosis
that hasn't actually been made. A category alongside the percentage
turns a red flag into an actionable signal instead of just a number to
worry about.

## Constraints
Every red-flag record must carry both a percentage and a category — a
percentage alone is not a valid record.

## Rejected
A — a percentage without a mechanism is false precision.

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
