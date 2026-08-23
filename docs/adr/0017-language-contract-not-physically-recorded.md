---
id: ADR-0017
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0017 — Language contract for Claude Code was never physically recorded

## Status

ACTIVE (the fix). Fix confirmed working for new files; not retroactively
applied to existing files.

## Context & Constraints

The rule existed only in the architect-side context (Google Drive
canonical documents), which Claude Code has no access to. Assuming
inheritance meant the rule silently never reached the one place it
needed to apply — restating it explicitly, every time, removes that
assumption entirely rather than hoping it holds.

The language contract line item is mandatory in every context file
prepared before a `/spec` session — not optional, not assumed present
from a prior session.

## Decision

Explicitly include the language contract ("agent-facing artifacts must
be in English") in every context file prepared before a `/spec` session.

## Alternatives & Rationale

A — assume Claude Code inherits the rule from context automatically. B —
explicitly restate the rule in every pre-`/spec` context file (chosen).

B.

A — proven wrong in practice: three files were written in Russian before
this fix, precisely because the rule was assumed inherited and never
was.

## Consequences

Implemented — the rule is now a mandatory line item in the pre-`/spec`
context file. Not retroactively fixed: three files
(`select_pilot_atoms.py`, `build_pilot_output.py`, `extraction_rules.md`)
remain in Russian, explicitly deferred as a known, non-blocking debt.

## Confirmation & Revisit

Confirmed for new work: Evidence Package code (written after the
contract was added to the context file) is entirely in English, no
violations.

None specified — deferred translation of the three existing files has no
target date.

**Source.** Claude Code audit at the owner's request.
