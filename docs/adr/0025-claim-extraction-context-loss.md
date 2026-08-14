# 0025 — Claim Extraction loses domain and specificity when forming novelty+basis

## Status
ACTIVE (diagnosis). Not yet resolved — a fix requires a new architectural
component, not yet designed.

## Decision
The failure point is one layer earlier than Evidence Package — inside
Claim Extraction (Layer 2), not inside search/evidence acquisition
(Layer 1, which was checked separately and found clean).

## Options
A — the `verified` criterion itself is wrong. B — Linkup truncates
returned content. C — Claim Extraction's `novelty + basis` formula loses
information needed for effective search (chosen, after A and B were
ruled out).

## Chosen
C.

## Why
Evidence Package's first live pilot returned 5 of 5 Claims as
unverifiable — a result that could mean the verification criterion
itself is wrong, that the search layer is silently losing data, or that
the input to search was already impoverished before it arrived. Ruling
out B directly (content confirmed unmodified at 3803 characters on a
verified example) and setting A aside pending a Layer 2 fix left C as
the explanation actually supported by a line-by-line comparison of the
data.

## Constraints
No fix to Evidence Package's `verified` criterion (option A) should be
attempted until this Layer 2 issue is resolved — changing two variables
at once would make it impossible to tell which fix caused which effect.

## Rejected
A — not ruled out entirely, but deliberately deferred pending the Layer
2 fix rather than pursued in parallel, to avoid mixing diagnostic
variables. B — ruled out directly; content was confirmed unmodified.

## Consequences
Diagnosed, not fixed. A line-by-line comparison of full atom text against
`novelty.value + basis.value` across all 5 pilot Claims showed a
systematic pattern (present in 4 of 5 claims): loss of domain/tag
context (which exists only in the graph's tags and wiki-links, and the
extraction schema does not carry it forward), and loss of the most
concrete, findable elements of the underlying thesis (examples, named
roles, connection to current discourse). One Claim additionally showed a
shift in modality during extraction (a direct assertion became a hedged
"analogy"). Direct, previously unstated connection to 0013: this is a
real instance of 0013's reversal condition firing. No other document
states this connection explicitly before this record.

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
