---
id: ADR-0001
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0001 — Capability is Article Pipeline logic, not a Brain data structure

## Status

ACTIVE.

## Context & Constraints

Brain is the owner's personal knowledge base and must not be shaped
around a downstream consumer's needs. Keeping Capability inside Article
Pipeline keeps Brain a passive, unmodified source, and lets it be read
through a single narrow, auditable channel (see 0022) instead of
scattering Article-Pipeline-specific structure through the owner's
personal graph.

Brain remains read-only from Article Pipeline's perspective. Reading
happens only through the channel defined in 0022, not ad hoc filesystem
access.

## Decision

Capability lives inside Article Pipeline as code, not inside Brain as a
MOC cluster or atom tags.

## Alternatives & Rationale

A — MOC cluster inside Brain. B — Tag on atoms. C — Logic inside Article
Pipeline (chosen).

C.

A (MOC cluster) — couples Brain's structure to Article Pipeline.
B (tag on atoms) — same coupling problem, different mechanism.

## Consequences

Brain is not modified by Article Pipeline. No architectural cleanup is
needed inside Brain if Article Pipeline changes or is removed.

## Confirmation & Revisit

Unverified — no automated check confirms Article Pipeline never writes
to Brain. This is a stated intent, not a tested invariant.

None specified.

**Source.** Explicit owner decision.
