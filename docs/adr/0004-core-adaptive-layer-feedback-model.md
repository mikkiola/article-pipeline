# 0004 — Core / adaptive layer / feedback loop architecture

## Status
ACTIVE. Declared architecture; the feedback-loop components it describes
are not implemented. Cited as settled fact in at least one downstream
document despite its origin explicitly marking it "not final" — flagged
for attention when ARCHITECTURE.md is written.

## Decision
Three invariants form an unchanging core: Intent/Meaning (the owner's,
untouchable), Evidence (what separates knowledge from fiction), Learning
(memory of what did and didn't work). Everything platform-specific —
format, hook, provocation level — is an adaptive layer, replaceable
without touching the core.

## Options
A — virality as a core principle (see 0002, rejected/reversed). B —
core/adaptive-layer/feedback model (chosen).

## Chosen
B.

## Why
Hardcoding platform-specific mechanics — as the original `agent.py` did
— breaks every time a platform's algorithm changes. Separating what must
never change (meaning, evidence, learning) from what should be freely
replaceable (format, voice, provocation) means a platform shift never
requires touching the parts that encode the owner's actual intent. A
direct contradiction was also found and resolved against the owner's
own personal knowledge graph, which independently supported this
separation.

## Constraints
Formalized as: "Source of meaning — the owner. Source of constraints —
reality (Evidence). The system optimizes the path between them." This
formula is treated as binding across all downstream architectural
decisions for Article Pipeline.

## Rejected
A (virality as core) — already covered in 0002.

## Consequences
Cited in canonical documents as adopted architecture. The components
that would implement the feedback loop (Experiment Log, Strategy Layer)
do not exist in code — this is a declaration, not a running cycle, and
should not be read as one.

## Validation
Unverified. The formula is quoted across canonical documents as accepted
but has never been exercised through a full
Hypothesis→Strategy→Publish→Observe→Evaluate cycle.

## Reversal condition
None specified.

## Source
Extended owner analysis, cross-checked against the owner's personal
knowledge graph.
