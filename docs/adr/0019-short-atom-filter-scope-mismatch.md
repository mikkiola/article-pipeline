---
id: ADR-0019
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0019 — The "under 80 characters" filter rule belongs to Drift, not Article Pipeline

## Status

ACTIVE (the correction). Confirmed against actual code.

## Context & Constraints

A rule filtering out very short atoms (under 80 characters) was decided
for System Drift/Collision Engine before the two products were split —
carrying it forward by default, just because it physically exists in
shared project history, would silently apply a Drift-specific decision
to Article Pipeline without ever checking whether it actually made
sense there.

Any rule found in shared project history must be checked against actual
code before being written into a context file for either product — not
assumed to apply to both just because it's mentioned somewhere in common
history.

## Decision

Do not carry a rule from one product's history into the other without a
separate, explicit justification for that product — even when both
products share the same repository history.

## Alternatives & Rationale

A — carry the rule forward into Article Pipeline since it exists
somewhere in the shared history. B — verify scope explicitly before
applying any inherited rule (chosen).

B.

A — proven wrong by direct code inspection: the rule was never actually
implemented in Article Pipeline's code at all.

## Consequences

Confirmed by reading the actual `atom_selector.py` code (`97b87f7`): it
contains only read-error handling, no length check. The rule genuinely
does not apply to Article Pipeline and was never implemented there.

## Confirmation & Revisit

Confirmed — direct code inspection against the mistaken written record,
discrepancy identified and explained (source-mixing between Drift and
Article Pipeline rules), not a missed implementation.

None specified.

**Source.** Direct conversation resolving the discrepancy.
