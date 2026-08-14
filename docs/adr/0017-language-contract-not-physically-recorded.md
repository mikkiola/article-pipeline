# 0017 — Language contract for Claude Code was never physically recorded

## Status
Accepted (the fix). Fix confirmed working for new files; not
retroactively applied to existing files.

## Context

The rule "agent-facing artifacts must be in English" existed only in
the architect-side context. Claude Code never saw it directly, since it
has no access to Google Drive where that rule lived.

## Decision

Explicitly include the language contract in every context file prepared
before a `/spec` session.

## Consequences

Implemented — the rule is now a mandatory line item in the pre-`/spec`
context file. **Not retroactively fixed**: three files
(`select_pilot_atoms.py`, `build_pilot_output.py`, `extraction_rules.md`)
remain in Russian, explicitly deferred as a known, non-blocking debt.

## Validation
Confirmed for new work: Evidence Package code (written after the
contract was added to the context file) is entirely in English, no
violations.

## Reversal condition
None specified — deferred translation of the three existing files has
no target date.

## Source
Claude Code audit at the owner's request.
