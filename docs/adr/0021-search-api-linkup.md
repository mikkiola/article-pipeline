# 0021 — Search API for Evidence Package: Linkup

## Status
Accepted. Implemented, in production.

## Context

Evidence Package needs an external search backend to verify Claim
sources.

## Decision

Linkup — the only candidate with a public, reproducible benchmark
specifically for factual accuracy (91-92% F-score on SimpleQA).

## Options considered

**Tavily.** Rejected — no public factual-accuracy benchmark, ownership-
change risk noted.

**Exa.** Rejected — no public factual-accuracy benchmark.

**Perplexity.** Rejected — no free API tier.

**Linkup (chosen).**

## Consequences

In production use: 5 real queries executed in the pilot run
(2026-08-13), budget not exhausted.

## Validation
Confirmed — real API calls, content not truncated by the pipeline
(3803 characters observed on a verified example), checked twice (before
and after the 0024 refactor).

## Reversal condition
None specified.

## Source
Cross-check across 5 independent external AI reviews, plus the
architect's own live verification (which caught and corrected two cases
of stale information from the external reviews).
