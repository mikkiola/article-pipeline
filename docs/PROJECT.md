# Article Pipeline — Project

Why this system exists, what it must ultimately prove, and where the
line between built and not-yet-built sits. For current per-component
state, see `docs/ARCHITECTURE.md`. For priorities and sequencing, see
`docs/ROADMAP.md`. For rationale behind any decision, see `docs/adr/`.
This document does not duplicate any of those three — it states only
what none of them are structured to hold.

## System Goal

Article Pipeline automatically turns the owner's real engineering work
into published, audience-appropriate content, without manual assembly,
and produces a regular, accumulating public professional record of
that work.

## System Outcome

The only outcome this system can prove by itself: a piece of content
was generated from real work and published automatically, with no
manual copy-paste step. Whether that content is seen, read, or leads
to any external opportunity is outside this system's ability to prove
— not a weaker goal, just not a claim this repository's tooling can
verify.

## Current vs. Target (top-level)

**Current:** the system produces publication-ready drafts (LinkedIn,
Habr) from real data. No channel publishes automatically today.

**Target:** every claimed content channel publishes automatically,
end to end, from real data, with no manual step.

See `docs/ARCHITECTURE.md` for exactly which components exist today
and `docs/ROADMAP.md` for what's next.

## Definition of Done — automatic publication (system-level, channel-agnostic)

A content channel counts as done when it publishes automatically, on
real data (not test fixtures), with zero manual steps between
generation and publication. This definition does not name a specific
channel — which channels are currently claimed, and each one's status
against this bar, lives in `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`,
not here. Adding a new channel does not require rewriting this
definition.

## Boundary: Direction Control / Analyzer

Weekly self-review of the owner's actual work direction against stated
goals is a separate system (`mikkiola/analyzer`). This repository does
not implement, track, or duplicate its goal model, data, or state — if
a task touches that concern, it belongs in `analyzer`'s own repository
and specification, not here.
