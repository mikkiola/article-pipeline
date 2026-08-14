# 0022 — Obsidian access channel: obsidian-local-rest-api

## Status
Accepted. Decision recorded, not physically used by any live component
yet.

## Context

An auditable channel for reading Brain is required (follows from 0001).

## Decision

`obsidian-local-rest-api` — a single audit point through a REST API key
— over direct filesystem access.

## Options considered

**kObsidian.** Rejected — filesystem-first design does not provide the
separation between access and audit that this project requires, despite
having a permissive (MIT) license.

**obsidian-local-rest-api (chosen).**

## Consequences

Decision is recorded but not wired into any live component — Evidence
Package currently works only with local Claim Extraction JSON output,
not through this channel.

## Validation
Unverified. A constraint (requires Obsidian running, not headless-
compatible) was inherited from external reviews without a separate
live check by the architect on this specific point.

## Reversal condition
Would need re-evaluation if headless (no running Obsidian instance)
operation becomes a requirement — not yet checked.

## Source
Cross-check across 5 independent external AI reviews, plus live GitHub
verification (2.7k stars, release 5.1.0 confirmed).
