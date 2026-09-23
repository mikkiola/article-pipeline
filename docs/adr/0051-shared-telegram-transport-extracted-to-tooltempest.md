---
id: ADR-0051
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0051: Shared Telegram transport extracted to ToolTempest

## Status

Accepted.

## Context & Constraints

The Publication Core Loop's Telegram HITL bot (owner review/approval of Change
Proposals per ADR-0050, and manual content review) needs a Telegram send +
receive transport. Before designing it, this repo's own `/spec` pre-spec check
(`finding-unknowns`, 2026-09-23) found that this exact transport pattern
already exists twice in this owner's ecosystem, not once:

- `mikkiola/radar/src/telegram_post.py` — `sendMessage`, `TELEGRAM_BOT_TOKEN`
  env-var convention.
- `mikkiola/analyzer/scripts/telegram_bot.py` — `sendMessage` plus
  `get_updates()` (cron-polling `getUpdates`, persisted offset, chat_id
  filtering, no webhook/always-on service). Its own module docstring states
  the send half's `TELEGRAM_BOT_TOKEN` convention was "reused verbatim from
  `radar/src/telegram_post.py` (confirmed by direct read this session)" —
  confirmed again by direct read here, 2026-09-23.

A third, independent copy in article-pipeline would be the third instance of
the same transport pattern (radar → analyzer → article-pipeline) — past the
point of "looks similar today" and into confirmed, recurring duplication.
This is the exact risk `docs/CONSTITUTION.md` already names as a recurring
problem in this project ("the same concept encoded in two places that then
silently drifted apart") and the reason ToolTempest exists at all as shared,
vendored tooling for this ecosystem (`/spec`, `/verify`, `drift-control.md`
today).

## Decision

Extract only the transport primitives actually duplicated today — send via
`sendMessage`, receive via cron-polling `getUpdates` with a persisted offset
and chat_id filtering — into ToolTempest as shared, vendored tooling, the
same role ToolTempest already plays for `/spec` and `/verify`. Not a
general-purpose Telegram framework: business logic (message formatting,
reply parsing, HITL approval semantics, decision templates) stays in each
consuming project, exactly as `analyzer/scripts/telegram_bot.py`'s own
`format_*` functions and `radar`'s posting logic are not part of what's
extracted.

This ADR records the decision to extract and its scope boundary. It does not
design the extraction itself (module layout, function signatures, ToolTempest
vendoring mechanics) — that is separate implementation work, filed as
`docs/BACKLOG.md`'s `[B-065]`.

This decision does not block article-pipeline's `/spec` interview for the
Publication Core Loop. The interview proceeds now, naming the ToolTempest-
shared transport as a stated dependency of the Telegram HITL bot milestone —
not something this ADR resolves by itself.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| **A. Build article-pipeline's Telegram bot independently, no reuse** | Rejected. Would be the third independent copy of the identical send/receive-with-offset-poll pattern — exactly the drift risk ToolTempest exists to prevent, not a hypothetical one. |
| **B. article-pipeline depends directly on `mikkiola/analyzer`'s script** | Rejected. Not vendored/shared tooling — a direct cross-repo dependency article-pipeline has no mechanism to consume safely (no lock-pin, no manifest, no version drift warning), unlike ToolTempest's existing `.tooltempest.lock`/`MANIFEST.txt` consumer contract. |
| **C. Extract the narrowly-scoped transport primitives into ToolTempest** | Chosen. A technical, business-logic-independent transport client (HTTP calls to Telegram's API, offset bookkeeping, chat_id filtering) is the standard case for sharing; business logic stays per-project. Matches ToolTempest's existing role and consumer contract exactly. |

## Consequences

- `docs/BACKLOG.md`'s `[B-065]` tracks the actual extraction; the
  implementation work happens in `mikkiola/tooltempest`, not here — same
  filing convention as `[B-023]` (ToolTempest CI), since ToolTempest has no
  backlog of its own.
- The Publication Core Loop `/spec` interview states the shared transport as
  a named precondition of its Telegram HITL bot milestone — that milestone's
  own "done when" cannot close until article-pipeline vendors and consumes
  the shared transport via the usual `.tooltempest.lock`/`MANIFEST.txt`
  mechanism, not a fresh copy.
- `radar`'s and `analyzer`'s own existing transport code is untouched by this
  ADR. Migrating them to consume the new shared version, if ever done, is a
  separate, later decision — not scoped here.

## Confirmation & Revisit

Confirmed when: ToolTempest's shared transport exists and is vendored into
article-pipeline (not a fresh copy), and at least one real send and one real
receive round-trip work end-to-end against the owner's real Telegram chat.

Revisit if the extraction turns out to need behavior that can't stay
generic — e.g., HITL-specific message formatting bleeding into what was
meant to be a pure transport layer — via a new, superseding ADR.

**Source.** Owner decision, 2026-09-23, resolving a BLOCKING finding from
this repo's own `/spec` pre-spec check (`finding-unknowns`): building a new
Telegram bot for article-pipeline without checking existing components would
have violated `docs/CONSTITUTION.md`'s unconditional "verify no existing
component covers this responsibility" rule.
