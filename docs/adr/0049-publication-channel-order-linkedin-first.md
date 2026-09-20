---
id: ADR-0049
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0049: Publication channel order — LinkedIn before Habr

## Status

Accepted.

## Context & Constraints

The Publication Core Loop is done only when LinkedIn and Habr both publish automatically
on real data (docs/PROJECT.md, Definition of Done). No channel publishes automatically
today. ROADMAP's Platform Adapter row lists the order Habr → LinkedIn. This decision sets
the order for the loop's first build.

State of each channel on 2026-09-20:
- LinkedIn: the draft path exists and consumes Strategy Layer's verdict
  (author/daily_linkedin_author.py, the voice contract in ADR-0044). LinkedIn's official
  API can post to a member's personal profile with the w_member_social scope, which the
  Share on LinkedIn product grants without partner review. This comes from LinkedIn's
  documentation and developer guides, checked on 2026-09-20. This project has not called
  the API yet.
- Habr: the draft path is a structural multi-claim digest (ADR-0046). The committed
  content requirement — at least one code or artifact fragment and one external source
  per article — has no design and no evidence source (ROADMAP, open questions). A
  supported way to publish to Habr without a manual step is not confirmed. A search on
  2026-09-20 found an unofficial client for an old Habr API and a 2017 article that calls
  Habr's internal endpoints with browser cookies. Neither is confirmed as current and
  supported.

## Decision

Build the first automatic publication on LinkedIn, then build Habr. The Publication Core
Loop stays open until both channels publish automatically on real data. This decision
changes the build order only, not the scope of the loop. The publication registry
(BACKLOG B-064) must not contain fields specific to one platform. Check Habr's
publication route in parallel with the LinkedIn work.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| **A. Habr first** (the order in ROADMAP's Platform Adapter row before this decision) | Rejected. The Habr path has two unresolved blockers: no confirmed publication route and an undesigned content requirement. Both would stall the first end-to-end run. |
| **B. Both channels in parallel** | Rejected. Two unproven external integrations at once make a failure harder to attribute. The Habr blockers would also hold back a loop that LinkedIn can already prove. |
| **C. LinkedIn first, Habr second** | Chosen. LinkedIn has a documented self-serve publishing route and an implemented draft path. It gives the thinnest complete slice first: draft, publish, registry record. |

Prior art: the walking skeleton (Alistair Cockburn) and tracer bullets (The Pragmatic
Programmer) both build the thinnest end-to-end slice first, because integration points
are the main source of trouble. A risk-first order would attack Habr's unknown first.
The parallel check of Habr's publication route in the Decision covers that risk without
blocking the slice.

## Consequences

- ROADMAP's Platform Adapter row, Current pointer, and committed-order note change to
  match this order.
- The first Platform Adapter work targets LinkedIn only. The registry and the adapter
  interface must accept a second platform without a redesign.
- Habr's first task is to confirm a supported publication route. If none exists, Habr
  cannot meet the "no manual step" bar in the usual way. The owner decides how to
  proceed. This ADR does not decide that.
- Third-party guides report that a personal-profile posting token expires after about
  60 days, so the LinkedIn adapter needs a token-renewal path.

## Confirmation & Revisit

Not yet exercised: no post has been published. This decision is confirmed when the first
automatic LinkedIn post publishes on real data and its record appears in the registry.
Revisit it if LinkedIn's API path requires a review or permission this project cannot
obtain, or if Habr's publication route turns out simpler than LinkedIn's.

**Source.** Architect decision, 2026-09-20. It follows the owner's master execution plan
(LinkedIn first), checked against the canonical docs. LinkedIn and Habr API
documentation and prior art were searched on 2026-09-20.
