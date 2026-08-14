# 0013 — Single atom vs. subgraph for Claim Extraction

## Status
Accepted. Reversal condition triggered on 2026-08-13 — see note below.
Not formally cross-referenced anywhere else at time of writing.

## Context

The owner's personal knowledge graph contains an atom stating "an
article is a byproduct of graph evolution," which conflicts with a
strict "one atom produces one article" assumption.

## Decision

Phase 1 starts with a simplified "one atom → one Claim" version as a
deliberate scope reduction for the pilot, not as a permanent
architectural principle. The full subgraph version (cluster/MOC/semantic
grouping — not yet defined which) is explicitly out of scope for this
phase.

## Options considered

**A — Full subgraph version from the start.** Rejected as premature —
"subgraph" itself is not yet defined, and building for an undefined
target risks wasted work.

**B — Single-atom simplification for the pilot (chosen).**

## Consequences

Implemented: Claim Extraction pilot ran on 13 atoms (2026-08-11) using
the single-atom version. The full subgraph version has not been started
— open question, tracked in the backlog.

## Validation
Confirmed for the single-atom version: 4 immutable pilot runs, 13 atoms,
baseline manually verified by the owner.

## Reversal condition
**[Triggered, not yet formally recorded elsewhere]**: "If the pilot
shows systemic context loss in single atoms, move to the subgraph
approach earlier than planned." ADR 0025 (2026-08-13) is a direct
instance of exactly this condition firing — the pilot did show systemic
context loss. No other document currently states explicitly that
0013's reversal condition has fired; this ADR records that connection.

## Source
Cross-check against the owner's personal knowledge graph, plus explicit
owner decision.
