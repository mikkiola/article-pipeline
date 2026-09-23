---
id: ADR-0053
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0053: content_id ownership moves from Registry to caller

## Status

Accepted.

## Context & Constraints

M1's Publication Registry (SPEC.md Functional Requirement #3) originally stated
`content_id` is "the Registry's own minted primary key." The initial
implementation (`publication_registry/writer.py`, commit `13000a9`) minted it via
`mint_content_id()` — a UTC timestamp, matching this project's existing
`run_id`/Claim-ID convention. A follow-up task (commit `8cfe791`) found a bare
content_id-collision check insufficient — it couldn't distinguish a genuine retry
from a real conflict — and built a secondary identity model, `(claim_id,
platform)`, to reconcile a collision before deciding whether to treat it as
idempotent or fatal.

A subsequent read-only investigation (this session) checked whether any
component in this repo — SPEC.md's M2/M4 text, `author/`, `strategy_layer/
write_verdict.py`'s `run_id`, and ADR-0044 through ADR-0052 — already defines or
plans a stable, pre-`content_id` identifier for "one logical publication
attempt." None does: `content_id`, minted by the Registry itself, was the only
identifier this system defined for a publication event, and by construction it
didn't exist yet at the moment identity needed to be established.

Separately, review found `(claim_id, platform)` — commit `8cfe791`'s identity
model — is itself insufficient, for the same underlying reason `claim_id` alone
was already rejected as the primary key: SPEC.md Functional Requirement #2 states
the same Claim can legitimately be published more than once. Two separate,
both-valid publications of the same Claim on the same platform share `(claim_id,
platform)` and would be incorrectly treated as the same event by that model,
causing a legitimate second publication to be rejected as a state conflict.
`url` cannot fill the gap either: it is undefined for a blocked publication
record (Functional Requirement #9 writes a Registry record on a bootstrap-gate
block even though nothing was actually posted, so no real per-attempt-unique URL
necessarily exists for that record).

The root cause underlying both prior attempts: `content_id` was being generated
by the Registry (the "server") rather than supplied by the caller (the
"client"). This is a known anti-pattern in idempotency-key design — a
server-generated key differs on every call by construction, which defeats
deduplication before any comparison logic can even run. No amount of post-hoc
field-comparison inside the writer can substitute for the caller supplying a
value that is actually stable across retries of the same logical event, because
the writer has no way to know, from inside a single call, what "the same event"
means to the caller.

## Decision

`content_id` is the stable identity of one logical publication event, and MUST
be supplied by the caller — never minted by the Registry writer, and never
reconstructed by the writer from `claim_id`, `platform`, `url`, or any other
`PublicationRecord` field combination.

This supersedes SPEC.md's Functional Requirement #3 wording ("`content_id` is
the Registry's own minted primary key") on the minting-location point
specifically — per `docs/CONSTITUTION.md`'s own doc-priority rule (ADR wins for
rationale; `docs/ARCHITECTURE.md` wins for current state), this ADR is now the
operative source for who mints `content_id`. SPEC.md's text itself is not
hand-edited by this decision: SPEC.md is the Living Spec, replaced wholesale by
a future `/spec` session, never patched in place outside one. The rest of
Functional Requirement #3 — `content_id`, not `claim_id`, is the primary key —
is unchanged and remains correct; only "the Registry's own minted" is
superseded.

`publication_registry/writer.py`'s `write_record()` is simplified to four
outcomes, since the writer no longer reconstructs identity from record fields —
`content_id` itself already IS the identity, by the caller's own construction:

1. No file at `{content_id}.json` → create, return the new path.
2. Existing file unreadable or doesn't parse as a `PublicationRecord` →
   `PublicationRegistryConflictError`, no overwrite.
3. Existing file readable, matches the incoming record on every field except
   `published_at`/`gate_evaluated_at` (which may legitimately differ across
   calls describing the same event — e.g. a retry that regenerates timestamps)
   → idempotent success, return the existing path, no rewrite.
4. Existing file readable but disagrees on any other field →
   `PublicationRegistryConflictError`, no overwrite.

The algorithm M2 (LinkedIn) or M4 (Habr) will each use to compute a stable
`content_id` for their own publication attempts is explicitly out of scope for
this decision — that remains each milestone's own future scoping work.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Registry mints `content_id` (original M1 design, commit `13000a9`) | Rejected. A server-generated key differs on every call by construction — defeats deduplication/retry-detection before any comparison logic runs. |
| B. Registry mints `content_id`, reconstructs identity from other fields to detect retries — `(claim_id, platform)`, commit `8cfe791` | Rejected. Every field or field-combination tried (`claim_id` alone, `claim_id`+`platform`, +`url`) is either insufficient (a Claim can be published more than once, so `claim_id`-based identity conflates legitimate separate publications) or undefined for some record (`url` has no value for a blocked publication). No reconstructable identity exists inside `PublicationRecord`'s own fields. |
| C. Chosen — caller supplies `content_id`; writer only persists and reconciles by field agreement | The party that knows what logical event is being recorded (the caller — eventually M2/M4) is the only party that can supply a value stable across retries of that same event. The writer's job narrows to what it can actually do reliably: persist-if-new, detect-and-refuse-if-conflicting. |

## Consequences

- `publication_registry/contract.py` is unchanged structurally — `content_id`
  was already a required `PublicationRecord` field with no minting logic in the
  model itself; only its own docstring's description of who mints it is
  corrected to point here.
- `publication_registry/writer.py`: `mint_content_id()` is removed entirely.
  `write_record()`'s five-outcome model (commit `8cfe791`) collapses to four —
  the identity-vs-agreement-field split it introduced is no longer meaningful
  once the writer isn't reconstructing identity.
- M2 and M4 (both Not started) each now carry an explicit, not-yet-resolved
  obligation: define how their own `content_id` value is computed and kept
  stable across retries of the same logical publication attempt. This is new,
  real scope neither milestone's current SPEC.md text names — flagged here, not
  resolved here.
- `docs/ARCHITECTURE.md`'s Publication Registry row is updated in the same
  commit as this ADR, since its existing Validation-column wording described a
  "mint+write+read round-trip" that no longer exists.

## Confirmation & Revisit

Confirmed when M2 or M4 first supplies a real, caller-computed `content_id` to
`write_record()` and a genuine retry (the same logical attempt, called twice) is
observed to return idempotent success rather than a spurious conflict.

Revisit if M2/M4 scoping concludes no computable, pre-write-stable value can be
derived for a given channel's publication attempts (e.g., if LinkedIn's own API
offers no deterministic way to predict a future post's identity before
publishing) — that would require a different mechanism (e.g., a caller-owned
attempt-ledger with its own retry semantics ahead of the Registry) and a new
ADR, not a patch to this one.

**Source.** Owner decision, 2026-09-23, following this session's read-only
investigation confirming no pre-`content_id` attempt identifier exists anywhere
in this repo, and a direct review finding commit `8cfe791`'s `(claim_id,
platform)` identity model insufficient per SPEC.md Functional Requirement #2.
