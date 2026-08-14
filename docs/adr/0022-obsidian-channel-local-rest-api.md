# 0022 — Obsidian access channel: obsidian-local-rest-api

## Status
ACTIVE. Decision recorded, not physically used by any live component
yet.

## Decision
`obsidian-local-rest-api` — a single audit point through a REST API key
— over direct filesystem access.

## Options
kObsidian, obsidian-local-rest-api (chosen).

## Chosen
obsidian-local-rest-api.

## Why
0001 requires an auditable channel for reading Brain — a filesystem-
first design (kObsidian) does not provide any separation between
"having access" and "an auditable record that access happened," which
is exactly the property this channel needs to have.

## Constraints
Requires a running Obsidian instance — not confirmed to work headless.
This constraint was inherited from external reviews, not independently
re-verified.

## Rejected
kObsidian — filesystem-first design does not provide the required
access/audit separation, despite having a permissive (MIT) license.

## Consequences
Decision is recorded but not wired into any live component — Evidence
Package currently works only with local Claim Extraction JSON output,
not through this channel.

## Validation
Unverified. The headless-compatibility constraint was inherited from
external reviews without a separate live check by the architect on this
specific point.

## Reversal condition
Would need re-evaluation if headless (no running Obsidian instance)
operation becomes a requirement — not yet checked.

## Source
Cross-check across 5 independent external AI reviews, plus live GitHub
verification (2.7k stars, release 5.1.0 confirmed).
