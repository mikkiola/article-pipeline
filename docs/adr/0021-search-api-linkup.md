---
id: ADR-0021
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0021 — Search API for Evidence Package: Linkup

## Status

ACTIVE, implemented, in production.

## Context & Constraints

Evidence Package's entire purpose is verifying factual claims — a search
backend chosen without a public, reproducible factual-accuracy benchmark
would mean trusting the verification layer on faith. Linkup was the only
candidate that let this be checked independently rather than taken on a
vendor's word.

Search backend interface must remain swappable (`search(query) ->
list[SearchResult]`) so a future backend change does not require
touching the rest of Evidence Package.

## Decision

Linkup — the only candidate with a public, reproducible benchmark
specifically for factual accuracy (91-92% F-score on SimpleQA).

## Alternatives & Rationale

Tavily, Exa, Perplexity, Linkup (chosen).

Linkup.

Tavily — no public factual-accuracy benchmark, ownership-change risk
noted. Exa — no public factual-accuracy benchmark. Perplexity — no free
API tier.

## Consequences

In production use: 5 real queries executed in the pilot run
(2026-08-13), budget not exhausted.

## Confirmation & Revisit

Confirmed — real API calls, content not truncated by the pipeline (3803
characters observed on a verified example), checked twice (before and
after the 0024 refactor).

None specified.

**Source.** Cross-check across 5 independent external AI reviews, plus the
architect's own live verification, which caught and corrected two cases
of stale information from the external reviews.
