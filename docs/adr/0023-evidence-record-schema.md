# 0023 — Evidence record schema: source/license fields always present, plus searched_at

## Status
ACTIVE, implemented and confirmed on real data.

## Decision
`source_url` and `license` fields are always present in the record, even
when null, plus a mandatory `searched_at` field.

## Options
A — source_url null with no distinguishing field. B — source_url/license
always present, plus mandatory searched_at (chosen).

## Chosen
B.

## Why
A single `null` value for `source_url` cannot distinguish "never
attempted" (pending) from "attempted, found nothing" (unverifiable) —
those are two very different states for a downstream reader to
understand, and collapsing them into one null loses exactly the
information that matters most for interpreting a record honestly.

## Constraints
Every Evidence record must carry `source_url`, `license`, and
`searched_at` fields structurally, regardless of whether a search
succeeded.

## Rejected
A — cannot distinguish pending from unverifiable, the exact distinction
this schema exists to preserve.

## Consequences
Implemented from the first version of the specification, before any code
was written.

## Validation
Confirmed — upheld on all 5 records from the real 2026-08-13 pilot run
(all five show explicit nulls where applicable; the structural schema
invariant held).

## Reversal condition
None specified.

## Source
Cross-check across 3 independent external AI reviews, unanimous result,
neutral prompt with no steering toward a predetermined answer.
