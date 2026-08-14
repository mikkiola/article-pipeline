# 0012 — Causal modeling (do-calculus/SCM) is deferred, not rejected

## Status
ACTIVE, deferred capability. Activation condition not yet met.

## Decision
Deferred capability with an explicit activation condition: 20-30+
publications and a recurring pattern not explainable by simply reading
the log.

## Options
A — build causal modeling now. B — reject the capability outright. C —
defer with an explicit activation condition (chosen).

## Chosen
C.

## Why
A formal causal model requires dozens of real observations that do not
yet exist — building it now would mean designing against imagined data.
There is a meaningful difference between "postponed until data exists"
and "discarded as a bad idea," and losing that distinction risks either
prematurely building unused infrastructure or permanently losing a
capability that will genuinely be needed later.

## Constraints
Must not be silently built early "just in case" before the activation
condition is met — that would be the same premature-infrastructure
mistake the deferral is meant to prevent.

## Rejected
A — no data exists yet to design against. B — would lose a capability
this project is expected to eventually need.

## Consequences
Not implemented. The activation condition has clearly not been met —
Experiment Log itself does not exist yet, so there are zero logged
observations to draw a pattern from.

## Validation
Not applicable.

## Reversal condition
20-30+ publications plus a recurring, log-unexplainable pattern.

## Source
Unanimous agreement across three independent architectural reviews.
