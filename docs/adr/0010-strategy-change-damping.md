# 0010 — Damped strategy switching (MAX_STRATEGY_CHANGES_PER_N_POSTS)

## Status
Accepted. Not implemented — Strategy Layer does not exist yet, so this
rule cannot be technically exercised.

## Context

Switching strategy after a single bad result risks chaotic, reactive
behavior. A full Viable System Model (five-level Beer governance) was
judged excessive for a solo-developer scale.

## Decision

A simple config rule: don't change strategy more than once per N
publications, with an explicit exception for an unambiguous catastrophic
failure.

## Options considered

**A — Full VSM (5-level Beer model).** Rejected — excessive complexity
for the current scale; same effect achievable with one config line.

**B — Simple damping rule with catastrophe exception (chosen).**

## Consequences

Specified in the pipeline's functional requirements. Cannot be tested
until Strategy Layer exists.

## Validation
Not applicable.

## Reversal condition
None specified.

## Source
Unanimous agreement across three independent architectural reviews;
identified as a "cheap fix" in the scaling backlog.
