# 0014 — New repository: mikkiola/article-pipeline

## Status
Accepted. Partially implemented — see inconsistency noted below.

## Context

Article Pipeline is not architecturally required to live inside
`brain.git` (follows from 0001). A full code migration in a single
session was judged excessive.

## Decision

Compromise: create an empty scaffold repository now; defer full code
migration to a separate future task. Does not exactly match any single
one of the originally proposed options.

## Consequences

Implemented: repository created 2026-08-10. **Partially inconsistent
with its own stated plan**: Claim Extraction and Evidence Package were
written directly in the new repository (not staged through `brain.git`
first), while Atom Selector and `graph_reader.py` remain vendored copies
rather than migrated originals — the "scaffold now, code later" pattern
was not applied uniformly.

## Validation
Unverified — migration of Atom Selector/`graph_reader.py` to a single
source of truth has not started as of 2026-08-13.

## Reversal condition
None specified.

## Source
Explicit owner decision, made from a table of options.
