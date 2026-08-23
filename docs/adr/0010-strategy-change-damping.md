---
id: ADR-0010
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0010 — Damped strategy switching (MAX_STRATEGY_CHANGES_PER_N_POSTS)

## Status

ACTIVE, deferred implementation.

## Context & Constraints

Switching strategy after a single bad result risks chaotic, reactive
behavior that never lets any one strategy run long enough to be judged
fairly. A full VSM governance model would give the same practical
protection at solo-developer scale, but at a cost of complexity far
beyond what one config line achieves.

Damping threshold (`N`) lives in config, not hardcoded. The catastrophe
exception must be unambiguous — not a judgment call made mid-incident.

## Decision

A simple config rule: don't change strategy more than once per N
publications, with an explicit exception for an unambiguous catastrophic
failure.

## Alternatives & Rationale

A — full Viable System Model (5-level Beer governance). B — simple
damping rule with a catastrophe exception (chosen).

B.

A — excessive complexity for the current scale; same effect achievable
with one config line.

## Consequences

Specified in the pipeline's functional requirements. Cannot be tested
until Strategy Layer exists.

## Confirmation & Revisit

Not applicable.

None specified.

**Source.** Unanimous agreement across three independent architectural reviews;
identified as a "cheap fix" in the scaling backlog.
