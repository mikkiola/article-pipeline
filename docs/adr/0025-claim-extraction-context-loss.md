# 0025 — Claim Extraction loses domain and specificity when forming novelty+basis

## Status
Accepted (diagnosis). Not yet resolved — a fix requires a new
architectural component, not yet designed.

## Context

Evidence Package's first live pilot returned 5 of 5 Claims as
unverifiable. The question was whether the weak result came from
Evidence Package itself or from something upstream.

## Decision

The failure point is one layer earlier than Evidence Package — inside
Claim Extraction (Layer 2), not inside search/evidence acquisition
(Layer 1, which was checked separately and found clean).

## Options considered

**A — The `verified` criterion itself is wrong.** Investigated,
not the primary explanation — deferred pending the Layer 2 fix (see
open backlog item on a proposed support-type classification).

**B — Linkup truncates returned content.** Ruled out directly — content
was confirmed unmodified (3803 characters observed on a verified
example).

**C — Claim Extraction's `novelty + basis` formula loses information
needed for effective search (chosen, after A and B were ruled out).**

## Consequences

Diagnosed, not fixed. A line-by-line comparison of full atom text
against `novelty.value + basis.value` across all 5 pilot Claims showed a
systematic pattern (present in 4 of 5 claims): loss of domain/tag
context (which exists only in the graph's tags and wiki-links, and the
extraction schema does not carry it forward), and loss of the most
concrete, findable elements of the underlying thesis (examples, named
roles, connection to current discourse). One Claim additionally showed a
shift in modality during extraction (a direct assertion became a hedged
"analogy").

**Direct, previously unstated connection to 0013**: this is a real
instance of 0013's reversal condition firing — "if the pilot shows
systemic context loss in single atoms, move to the subgraph approach
earlier than planned." No other document states this connection
explicitly before this ADR.

## Validation
Confirmed — line-by-line comparison across all 5 pilot Claims, Layer 1
separately ruled out by direct inspection.

## Reversal condition
Resolved once a context/causal-structure layer between Claim Extraction
and Evidence Package is designed and implemented — tracked as a
following session's primary task.

## Source
Architect diagnosis performed by Claude Code at the owner's direct
request, after explicitly ruling out the alternative hypotheses above.
