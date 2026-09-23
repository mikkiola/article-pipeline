---
id: ADR-0054
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0054: M2 ships core LinkedIn publishing without SAFETY_PAUSE's trigger or proactive token-expiry alerting

## Status

Accepted.

## Context & Constraints

SPEC.md's committed milestone order ships M2 (LinkedIn Auto-Publish) before M3
(Owner Verdict) and M5 (Telegram HITL Bot). A read-only scoping pass (this
session, prior task) found that M2's own Functional Requirements name two
mechanisms whose real delivery depends on milestones that don't exist yet:

> 10. **Circuit breaker — `SAFETY_PAUSE`.** One explicit `trash` Owner Verdict
>     on an already-published LinkedIn post opens the circuit: future
>     scheduled auto-publish runs are skipped while `SAFETY_PAUSE` is active.
>     ... (SPEC.md, Functional Requirements — M2, item 10)

`SAFETY_PAUSE`'s trigger is an Owner Verdict — M3's own Functional
Requirements 14-16 (`verdict/output/` event stream, `content_id`-keyed,
`good`/`trash`/`style-off`) define that mechanism; it does not exist yet
(SPEC.md's M3 Milestones entry: `status: not started`).

> 13. LinkedIn token renewal: a scheduled check tracks the token's known
>     ~60-day expiry (ADR-0049) and sends a Telegram alert before it expires
>     ... (SPEC.md, Functional Requirements — M2, item 13)

The alert-delivery channel is M5's Telegram bot — M5's own Functional
Requirement 23 names `SYSTEM_FAILURE`/`SAFETY_PAUSE` alerts and recovery
messages as one of its four responsibilities; M5 does not exist yet (SPEC.md's
M5 Milestones entry: `status: blocked on [B-065]`).

SPEC.md's text was checked directly (prior task, this session) for any
sequencing guidance — a stub, a deferred no-op, an interim alerting channel,
or an explicit "ships as a no-op until M3/M5 land" note. None exists anywhere
in the document. `docs/adr/0049-publication-channel-order-linkedin-first.md`
(the ADR establishing LinkedIn-before-Habr order) was also checked directly:
it discusses the token-renewal need in its Consequences section but says
nothing about M2's own internal dependency on M3/M5's not-yet-built
mechanisms. This is a real, undocumented sequencing gap in SPEC.md's text,
not something either prior check inferred or guessed at.

## Decision

M2 is split into independently-gateable capabilities rather than blocked on
M3/M5 or filled with throwaway interim mechanisms:

1. **Built now, real and complete on its own:** the scheduled workflow,
   caller-supplied `content_id` generation (`linkedin-{date}`, per
   docs/adr/0053-content-id-ownership-moves-to-caller.md), the bootstrap gate
   wiring (`strategy_layer/pre_filter.py`'s real `classify_unit()`/
   `check_gate_condition()` — not SPEC.md Functional Requirement #8's
   `check_all_claims_unverifiable_gate()`, a name that does not exist in the
   code; confirmed naming drift in SPEC.md's text, not fixed there per this
   project's Living-Spec convention), the LinkedIn API client, and
   Publication Registry integration (a `gate_status=pass` record on a
   successful publish, a `gate_status=block` record on a bootstrap-gate
   block, per Functional Requirement #9).
2. **A fail-closed token preflight stands in for Functional Requirement #13's
   proactive alert.** Before any LinkedIn API call, the token's presence and
   expiry are checked; on missing or expired, the run stops with no publish
   attempt and no Registry write. This is a real, complete safety property on
   its own — a bad or absent credential can never reach the LinkedIn API —
   and does not require M5's Telegram bot to exist. It is not a substitute
   for M5's eventual proactive "expiring soon" warning (that still requires
   M5), only for the "never publish on an invalid token" half of Functional
   Requirement #13.
3. **`SAFETY_PAUSE`'s state is defined and checked; its trigger is not
   built.** `linkedin_publisher/safety_pause.py` defines `CLOSED`/`OPEN` (no
   project precedent existed for these names — checked directly, none found;
   chosen as the standard circuit-breaker-pattern vocabulary) and a read-only
   check the scheduled job consults before attempting to publish. No code
   anywhere in this change ever writes `OPEN` — that write path is M3's Owner
   Verdict, deliberately not built here. The state starts and stays `CLOSED`
   until M3 exists.
4. **Named, explicit limitation, not a hidden gap:** a content-quality
   problem in the very first real publication cannot yet trigger
   `SAFETY_PAUSE` automatically, because the only defined trigger (one
   explicit `trash` Owner Verdict) has no mechanism to fire until M3 is
   built. Between M2 shipping and M3 shipping, a bad LinkedIn post can only
   be caught by the owner noticing it directly on LinkedIn — there is no
   automated circuit-breaker protection in that window. This is a real,
   accepted risk of the committed LinkedIn-before-M3 milestone order, not
   something this task's scope can close on its own.

This supersedes SPEC.md's M2 Milestones checklist wording — "`SAFETY_PAUSE`
circuit breaker" and "token-expiry alert" listed as flat, undifferentiated
checklist items alongside "Bootstrap gate wiring" and "LinkedIn API publish"
— by rationale, per this project's ADR-wins-for-rationale doc-priority rule.
SPEC.md's own text is not hand-edited by this decision: SPEC.md is the Living
Spec, replaced wholesale by a future `/spec` session, never patched in place
outside one.

Two further data-model limitations were found while implementing this split,
named here rather than silently resolved (see Consequences):
`publication_registry.contract.PublicationRecord.claim_id` is a singular
field, but a real LinkedIn post built from a daily_brief can aggregate
multiple included claims, and a bootstrap-gate block is a run-level outcome
with no single claim to name. `linkedin_publisher/daily_publish.py` uses the
first unit in run order as a representative `claim_id` in both cases.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Block M2 entirely until M3 and M5 both ship | Rejected. Contradicts the committed milestone order (M2 ships first) and this project's own walking-skeleton rationale (ADR-0049: "the thinnest complete slice first") for no benefit — `SAFETY_PAUSE` and the token alert are each independently buildable-or-not without blocking the rest of M2's real capability. |
| B. Build throwaway interim mechanisms (e.g. a fake `SAFETY_PAUSE` trigger keyed on something other than an Owner Verdict, or a substitute alert channel like email/log-file for token expiry) | Rejected, per this task's own explicit scope. A fake trigger would need to be un-built or migrated once M3's real Owner Verdict exists, and risks becoming a second, competing mechanism nobody remembers to retire. A substitute alert channel duplicates work M5 will do properly, and this project's Constitution favors not inventing a component when the responsibility is already scoped elsewhere. |
| C. Chosen — split M2 into what's real and complete now (scheduled publish, gate wiring, Registry integration, fail-closed token preflight) vs. what's explicitly named as blocked-pending (`SAFETY_PAUSE`'s trigger, proactive alerting) | Ships the thinnest real, honest slice: every mechanism built either works completely on its own (the preflight) or is correctly inert pending its real trigger (`SAFETY_PAUSE`'s `CLOSED` default), with the gap plainly named rather than hidden or faked. |

## Consequences

- `linkedin_publisher/` is a new component: `linkedin_client.py` (token
  preflight + the `POST /rest/posts` call),  `safety_pause.py` (state
  definition + read-only check, no writer), `daily_publish.py` (the
  scheduled job's real orchestration — Collector daily_brief through the
  existing, already-tested Strategy Layer + Author pipeline to a real
  LinkedIn publish and a real Publication Registry write).
- `SAFETY_PAUSE`'s `OPEN` trigger remains fully unbuilt. When M3 is
  eventually built, it must write `linkedin_publisher/state/
  safety_pause_state.json` (or supersede this state-storage choice with its
  own design) — not assumed to already have a write path from this change.
- `PublicationRecord.claim_id`'s singular-vs-multi-claim mismatch (see
  Decision) is not resolved here. A future task revisiting the schema to
  support multiple claims per publication would need its own decision, not
  a patch to this ADR.
- `LINKEDIN_ACCESS_TOKEN_EXPIRES_AT` and `LINKEDIN_PERSON_URN` are two
  additional owner-supplied environment variables this task discovered are
  required, beyond `LINKEDIN_ACCESS_TOKEN` alone — neither is named
  explicitly anywhere in SPEC.md's text. Both are manual setup, out of this
  task's scope, same as `LINKEDIN_ACCESS_TOKEN` itself.
- The new scheduled workflow needs read access to the separate, private
  `mikkiola/collector` repository (per `docs/BACKLOG.md`'s `[B-055]`) to
  check out each day's `daily_brief_<date>.json` — this requires a
  cross-repo credential (e.g. a PAT stored as a GitHub Actions secret) whose
  existence this task could not verify. Flagged as an owner-setup
  prerequisite, same treatment as the LinkedIn token itself.

## Confirmation & Revisit

Confirmed when M3 is built and its Owner Verdict mechanism can write `OPEN`
to `linkedin_publisher`'s `SAFETY_PAUSE` state file (or a superseding
mechanism), and independently when the fail-closed token preflight is
observed correctly blocking a real run on a missing or expired credential.

Revisit when M5 is built: at that point, Functional Requirement #13's
proactive "expiring soon" alert (still not built by this decision) becomes
buildable, and this ADR's Decision point 2 should be read as fulfilled only
for its fail-closed half, not the proactive-alert half, until that happens.

**Source.** Owner task, 2026-09-24, following this session's prior read-only
scoping pass (which found the SPEC.md/ADR-0049 sequencing gap this ADR
resolves) and the token-preflight/`SAFETY_PAUSE`-split reasoning specified in
that task directly.
