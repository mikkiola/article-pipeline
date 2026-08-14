# 0013 — Single atom vs. subgraph for Claim Extraction

## Status
ACTIVE. Reversal condition triggered on 2026-08-13 (see 0025) — not
formally cross-referenced anywhere else at time of writing, recorded
here explicitly.

## Decision
Phase 1 starts with a simplified "one atom → one Claim" version as a
deliberate scope reduction for the pilot, not as a permanent
architectural principle. The full subgraph version (cluster/MOC/semantic
grouping — not yet defined which) is explicitly out of scope for this
phase.

## Options
A — full subgraph version from the start. B — single-atom simplification
for the pilot (chosen).

## Chosen
B.

## Why
The owner's personal knowledge graph contains an atom stating "an
article is a byproduct of graph evolution," which conflicts with a
strict one-atom-to-one-article assumption — but building the full
subgraph version first would mean designing against an undefined target,
since "subgraph" itself (cluster? MOC? semantic grouping?) had not yet
been decided. Starting narrow lets the pilot surface whether the
simplification actually loses something important before committing to
a specific subgraph design.

## Constraints
The single-atom simplification must be explicitly labeled as a scope
reduction for the pilot, not represented anywhere as the permanent
architecture.

## Rejected
A — premature; "subgraph" itself is not yet defined, and building for an
undefined target risks wasted work.

## Consequences
Implemented: Claim Extraction pilot ran on 13 atoms (2026-08-11) using
the single-atom version. The full subgraph version has not been started
— open question, tracked in the backlog.

## Validation
Confirmed for the single-atom version: 4 immutable pilot runs, 13 atoms,
baseline manually verified by the owner.

## Reversal condition
"If the pilot shows systemic context loss in single atoms, move to the
subgraph approach earlier than planned." **Triggered**: 0025 (2026-08-13)
is a direct instance of exactly this condition firing — the pilot did
show systemic context loss. No other document currently states
explicitly that this reversal condition has fired; this record makes
that connection explicit.

## Source
Cross-check against the owner's personal knowledge graph, plus explicit
owner decision.
