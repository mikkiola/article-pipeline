# 0005 — Experiment Log: default status is "inconclusive," not a confidence number

## Status
Accepted. Not implemented (no Experiment Log code exists).

## Context

A numeric confidence score (e.g. "confidence: 0.62") with no defined
calculation method creates the appearance of precision without the
substance of it.

## Decision

Experiment Log records default to a status of `inconclusive` rather than
carrying a fabricated confidence number.

## Options considered

**A — Numeric confidence score.** Rejected — "a number that looks like
knowledge" is not knowledge without a defined method behind it.

**B — Status field, default `inconclusive` (chosen).**

## Consequences

Specified in the pipeline's functional requirements (record format
includes a `status: inconclusive` field). No code exists yet — the
component is fully deferred.

## Validation
Not applicable — no implementation exists to validate.

## Reversal condition
None specified.

## Source
Convergent input from three independent architectural reviews, plus
owner confirmation.
