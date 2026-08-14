# 0023 — Evidence record schema: source/license fields always present, plus searched_at

## Status
Accepted. Implemented and confirmed on real data.

## Context

A single `null` value for `source_url` is not enough to distinguish
"never attempted" (pending) from "attempted, found nothing"
(unverifiable).

## Decision

`source_url` and `license` fields are always present in the record, even
when null, plus a mandatory `searched_at` field.

## Consequences

Implemented from the first version of the specification, before any
code was written.

## Validation
Confirmed — upheld on all 5 records from the real 2026-08-13 pilot run
(all five show explicit nulls where applicable; the structural schema
invariant held).

## Reversal condition
None specified.

## Source
Cross-check across 3 independent external AI reviews, unanimous result,
neutral prompt with no steering toward a predetermined answer.
