# 0020 — Claim extraction rules A/B/C (fact/hypothesis, detection vs. filling, personal beliefs)

## Status
Accepted. Implemented and validated, including a specific counter-
hypothesis test.

## Context

The first Claim Extraction pilot run systematically failed in three
specific ways: (A) `basis` was tagged as FACT when it was actually a
logical inference; (B) claims were assigned `no_claim` due to incomplete
fields rather than genuine absence of a claim; (C) personal beliefs were
discarded based on grammatical person rather than content.

## Decision

Three rules: citability is necessary but not sufficient for a FACT tag;
detection and filling are handled as separate steps; grammatical person
is not a rejection criterion.

## Consequences

Implemented in `claim_extraction/extraction_rules.md`, applied across
four iterations on 13 atoms.

## Validation
Confirmed — the hypothesis "0/40 FACT tags is a property of the graph
itself" was explicitly tested and disproven on an independent sample of
5 new atoms (1/24 shown to be achievable, rare but real).

## Reversal condition
None specified.

## Source
Four rounds of manual owner verification, plus two independent AI
reviews.
