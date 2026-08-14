# 0010 — Damped strategy switching (MAX_STRATEGY_CHANGES_PER_N_POSTS)

## Status
ACTIVE, deferred implementation.

## Decision
A simple config rule: don't change strategy more than once per N
publications, with an explicit exception for an unambiguous catastrophic
failure.

## Options
A — full Viable System Model (5-level Beer governance). B — simple
damping rule with a catastrophe exception (chosen).

## Chosen
B.

## Why
Switching strategy after a single bad result risks chaotic, reactive
behavior that never lets any one strategy run long enough to be judged
fairly. A full VSM governance model would give the same practical
protection at solo-developer scale, but at a cost of complexity far
beyond what one config line achieves.

## Constraints
Damping threshold (`N`) lives in config, not hardcoded. The catastrophe
exception must be unambiguous — not a judgment call made mid-incident.

## Rejected
A — excessive complexity for the current scale; same effect achievable
with one config line.

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
