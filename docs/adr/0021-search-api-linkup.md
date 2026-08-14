# 0021 — Search API for Evidence Package: Linkup

## Status
ACTIVE, implemented, in production.

## Decision
Linkup — the only candidate with a public, reproducible benchmark
specifically for factual accuracy (91-92% F-score on SimpleQA).

## Options
Tavily, Exa, Perplexity, Linkup (chosen).

## Chosen
Linkup.

## Why
Evidence Package's entire purpose is verifying factual claims — a search
backend chosen without a public, reproducible factual-accuracy benchmark
would mean trusting the verification layer on faith. Linkup was the only
candidate that let this be checked independently rather than taken on a
vendor's word.

## Constraints
Search backend interface must remain swappable (`search(query) ->
list[SearchResult]`) so a future backend change does not require
touching the rest of Evidence Package.

## Rejected
Tavily — no public factual-accuracy benchmark, ownership-change risk
noted. Exa — no public factual-accuracy benchmark. Perplexity — no free
API tier.

## Consequences
In production use: 5 real queries executed in the pilot run
(2026-08-13), budget not exhausted.

## Validation
Confirmed — real API calls, content not truncated by the pipeline (3803
characters observed on a verified example), checked twice (before and
after the 0024 refactor).

## Reversal condition
None specified.

## Source
Cross-check across 5 independent external AI reviews, plus the
architect's own live verification, which caught and corrected two cases
of stale information from the external reviews.
