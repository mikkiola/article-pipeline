---
id: ADR-0007
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0007 — Strategy Layer is separate from Platform Adapter

## Status

ACTIVE, deferred implementation.

## Context & Constraints

The original `agent.py` hardcoded voice and framing directly into
generation code, which meant every strategy change required touching
publishing code and vice versa. Separating the three means a strategy
change never risks breaking technical publishing, and a new platform
adapter never requires re-deciding voice.

Platform Adapter must remain unaware of Strategy's reasoning — it only
executes what Author hands it, technically.

## Decision

Choice of framing/hook/voice (Strategy) is architecturally separated
from technical publishing (Platform Adapter). Strategy Layer outputs a
config; Author executes it; Adapter publishes without knowing about
strategy.

## Alternatives & Rationale

A — combine strategy and publishing logic, as `agent.py` did. B —
separate Strategy Layer, Author, and Platform Adapter (chosen).

B.

A — direct repeat of the known technical debt this project is moving
away from.

## Consequences

Specified in the pipeline design. None of the three components has been
implemented — all exist only as specification.

## Confirmation & Revisit

Not applicable — no implementation exists.

None specified.

**Source.** Unanimous agreement across three independent architectural reviews.
