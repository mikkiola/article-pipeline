# 0004 — Core / adaptive layer / feedback loop architecture

## Status
Accepted. Declared architecture; the feedback-loop components it
describes are not implemented.

## Context

Hardcoding platform-specific mechanics (as the original `agent.py` did)
breaks whenever a platform's algorithm changes. A more durable
separation was needed between what must never change and what should be
freely replaceable.

## Decision

Three invariants form an unchanging core: Intent/Meaning (the owner's,
untouchable), Evidence (what separates knowledge from fiction), and
Learning (memory of what did and didn't work). Everything
platform-specific — format, hook, provocation level — is an adaptive
layer, replaceable without touching the core.

## Options considered

**A — Virality as a core principle.** Rejected (see 0002).

**B — Core/adaptive-layer/feedback model (chosen).**

## Consequences

Formalized as: "Source of meaning — the owner. Source of constraints —
reality (Evidence). The system optimizes the path between them." Cited
in canonical documents as adopted architecture, but the components that
would implement the feedback loop (Experiment Log, Strategy Layer) do
not exist in code — this is a declaration, not a running cycle.

## Validation
Unverified. The formula is quoted across canonical documents as accepted
but has never been exercised through a full
Hypothesis→Strategy→Publish→Observe→Evaluate cycle.

## Reversal condition
None specified.

## Source
Extended owner analysis, cross-checked against the owner's personal
knowledge graph (a direct contradiction was found and resolved between
the prior architecture and an existing atom: "an article is a byproduct
of graph evolution").

**Caution for downstream documents:** this decision was recorded as "not
final" in its originating spec (ТЗ_ap_v2) but has since been cited as
settled fact in at least one other document — flag this if it recurs
when writing ARCHITECTURE.md.
