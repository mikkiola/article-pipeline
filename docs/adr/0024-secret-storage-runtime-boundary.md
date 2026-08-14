# 0024 — Secret storage is separated from the runtime secret-retrieval mechanism

## Status
Accepted. Implemented and committed. **Known open item: the written
specification (SPEC.md) has not been updated to match** — see
Consequences.

## Context

Production/CI code should not depend on the Bitwarden CLI as a runtime
mechanism for retrieving secrets.

## Decision

`search_backend.py` reads `LINKUP_API_KEY` exclusively from the
environment. No Bitwarden CLI call exists anywhere in the code path.
Bitwarden remains one way to populate that environment variable
locally; a CI masked variable is a future alternative, requiring no
code change.

## Options considered

**A — `bw get password` invoked directly inside the script (the
original SPEC.md-specified mechanism).** Rejected after implementation
began — couples runtime behavior to a specific secret manager CLI being
installed and unlocked.

**B — Fallback pattern: try environment first, then fall back to
Bitwarden CLI inside the code.** Rejected — still couples the code path
to Bitwarden as a fallback dependency.

**C — Environment variable only, Bitwarden is purely a way to populate
it locally (chosen).**

An intermediate `.bw_session` file approach was also considered and
rejected as an unnecessary extra moving part.

## Consequences

Implemented and committed (`b1527ae`). **Direct deviation from the
written SPEC.md**, which still specifies the old mechanism in three
places. This deviation is tracked via `drift-control`: goal deviation
score 0.2, explicitly logged as "approved deviation," combined score
0.10 — not zeroed out to hide the gap. **The written SPEC.md text has
not been updated to reflect this decision as of 2026-08-13** — flagged
as an open item for a following session.

## Validation
Confirmed — smoke-tested twice against the live Linkup API, before and
after the refactor, both times with real results.

## Reversal condition
None specified.

## Source
Explicit owner decision, made after the architect proposed two less
clean alternatives first.
