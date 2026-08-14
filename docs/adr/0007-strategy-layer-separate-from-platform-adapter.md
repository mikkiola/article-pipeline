# 0007 — Strategy Layer is separate from Platform Adapter

## Status
Accepted. Not implemented.

## Context

The original `agent.py` hardcoded voice and framing directly into
generation code — a known source of technical debt this project set out
to avoid repeating.

## Decision

Choice of framing/hook/voice (Strategy) is architecturally separated
from technical publishing (Platform Adapter). Strategy Layer outputs a
config; Author executes it; Adapter publishes without knowing about
strategy.

## Options considered

**A — Combine strategy and publishing logic (as `agent.py` did).**
Rejected — direct repeat of the known technical debt this project is
moving away from.

**B — Separate Strategy Layer, Author, and Platform Adapter (chosen).**

## Consequences

Specified in the pipeline design (functional requirements sections for
Strategy, Author, and Adapter). None of the three components has been
implemented — all exist only as specification.

## Validation
Not applicable — no implementation exists.

## Reversal condition
None specified.

## Source
Unanimous agreement across three independent architectural reviews.
