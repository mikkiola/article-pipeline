---
id: ADR-0005
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0005 — Experiment Log: default status is "inconclusive," not a confidence number

## Status

ACTIVE, deferred implementation.

## Context & Constraints

A number like "confidence: 0.62" with no defined calculation method
behind it looks precise but carries no real information — it invites
false trust. `inconclusive` as a default is honest about what the system
actually knows at a given point, and only moves off that default when
there's a real basis to do so.

Specified as a mandatory `status` field in every Experiment Log record
format.

## Decision

Experiment Log records default to a status of `inconclusive` rather than
carrying a fabricated confidence number.

## Alternatives & Rationale

A — numeric confidence score. B — status field, default `inconclusive`
(chosen).

B.

A — "a number that looks like knowledge" is not knowledge without a
defined method behind it.

## Consequences

Specified in the pipeline's functional requirements. No code exists yet
— the component is fully deferred.

## Confirmation & Revisit

Not applicable — no implementation exists to validate.

None specified.

**Source.** Convergent input from three independent architectural reviews, plus
owner confirmation.
