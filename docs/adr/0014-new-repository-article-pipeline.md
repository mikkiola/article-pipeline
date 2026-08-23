---
id: ADR-0014
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0014 — New repository: mikkiola/article-pipeline

## Status

ACTIVE, partially implemented — known inconsistency, see Consequences.

## Context & Constraints

Article Pipeline is not architecturally required to live inside
`brain.git` (follows from 0001), but a full code migration in the same
session as everything else being decided was judged an excessive load —
splitting scaffold creation from code migration let the repository exist
immediately without forcing a rushed migration.

New Article Pipeline code should be written directly into the new
repository going forward, not staged through brain.git first — though
this constraint was not applied uniformly in practice (see
Consequences).

## Decision

Compromise: create an empty scaffold repository now; defer full code
migration to a separate future task. Does not exactly match any single
one of the originally proposed options.

## Alternatives & Rationale

A — full immediate migration of all code from brain.git. B — leave
everything in brain.git indefinitely. C — scaffold now, migrate code
later as a separate task (chosen, as a compromise not identical to any
single proposed option).

C.

A — too much for a single session. B — leaves Article Pipeline
permanently coupled to brain.git, which 0001 already ruled out as the
long-term goal.

## Consequences

Implemented: repository created 2026-08-10. Partially inconsistent with
its own stated plan — Claim Extraction and Evidence Package were written
directly in the new repository (not staged through brain.git first),
while Atom Selector and `graph_reader.py` remain vendored copies rather
than migrated originals. The "scaffold now, code later" pattern was not
applied uniformly.

## Confirmation & Revisit

Unverified — migration of Atom Selector/`graph_reader.py` to a single
source of truth has not started as of 2026-08-13.

None specified.

**Source.** Explicit owner decision, made from a table of options.
