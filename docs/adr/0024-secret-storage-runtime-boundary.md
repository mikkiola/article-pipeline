---
id: ADR-0024
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0024 — Secret storage is separated from the runtime secret-retrieval mechanism

## Status

ACTIVE, implemented and committed. Known open item: the written
specification (SPEC.md) has not been updated to match — see
Consequences.

## Context & Constraints

Production/CI code should not depend on the Bitwarden CLI as a runtime
mechanism for retrieving secrets — a script that must have Bitwarden
installed and unlocked to run cannot run unattended in CI, and any
future secret source (a CI masked variable, for example) would require
new code paths under options A or B. Option C separates "how the secret
gets into the environment" from "how the code reads it," so the code
never needs to change when the storage mechanism does.

No Bitwarden CLI call may exist anywhere in `search_backend.py` or any
future Evidence Package code. The only supported read path is the
environment variable.

## Decision

`search_backend.py` reads `LINKUP_API_KEY` exclusively from the
environment. No Bitwarden CLI call exists anywhere in the code path.
Bitwarden remains one way to populate that environment variable locally;
a CI masked variable is a future alternative, requiring no code change.

## Alternatives & Rationale

A — `bw get password` invoked directly inside the script, the original
SPEC.md-specified mechanism. B — fallback pattern: environment first,
then Bitwarden CLI as fallback inside the code. C — environment variable
only, Bitwarden purely a way to populate it locally (chosen). An
intermediate `.bw_session` file approach was also considered.

C.

A — couples runtime behavior to a specific secret manager CLI being
installed and unlocked. B — still couples the code path to Bitwarden as
a fallback dependency. The `.bw_session` file approach — rejected as an
unnecessary extra moving part.

## Consequences

Implemented and committed (`b1527ae`). Direct deviation from the written
SPEC.md, which still specifies the old mechanism in three places. This
deviation is tracked via `drift-control`: goal deviation score 0.2,
explicitly logged as "approved deviation," combined score 0.10 — not
zeroed out to hide the gap. The written SPEC.md text has not been
updated to reflect this decision as of 2026-08-13 — flagged as an open
item for a following session.

## Confirmation & Revisit

Confirmed — smoke-tested twice against the live Linkup API, before and
after the refactor, both times with real results.

None specified.

**Source.** Explicit owner decision, made after the architect proposed two less
clean alternatives first.
