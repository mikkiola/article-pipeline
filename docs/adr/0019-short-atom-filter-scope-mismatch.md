# 0019 — The "under 80 characters" filter rule belongs to Drift, not Article Pipeline

## Status
Accepted (the correction). Confirmed against actual code.

## Context

A rule filtering out very short atoms (under 80 characters) was decided
for System Drift / Collision Engine before Article Pipeline and Drift
were split into separate projects. A context file prepared for Claude
Code mistakenly carried this rule into Article Pipeline scope.

## Decision

Do not carry a rule from one product's history into the other without a
separate, explicit justification for that product — even when both
products share the same repository history.

## Consequences

Confirmed by reading the actual `atom_selector.py` code (`97b87f7`):
it contains only read-error handling, no length check. The rule genuinely
does not apply to Article Pipeline and was never implemented there.

## Validation
Confirmed — direct code inspection against the mistaken written record,
discrepancy identified and explained (source-mixing between Drift and
Article Pipeline rules), not a missed implementation.

## Reversal condition
None specified.

## Source
Direct conversation resolving the discrepancy.
