# 0001 — Capability is Article Pipeline logic, not a Brain data structure

## Status
Accepted. Implementation: architectural intent, not technically enforced
as an invariant (no test verifies Article Pipeline never writes to
Brain).

## Context

Brain (the Obsidian knowledge graph) is the owner's personal knowledge
base. Article Pipeline needs to read from it. The question is whether
Article Pipeline's selection/capability logic should live inside Brain's
own structure (as a MOC cluster or a tag on atoms) or entirely outside
it.

## Decision

Capability lives inside Article Pipeline as code, not inside Brain as a
MOC cluster or atom tags.

## Options considered

**A — MOC cluster inside Brain.** Rejected: makes Brain's structure
depend on Article Pipeline's needs, coupling the personal knowledge base
to a downstream consumer.

**B — Tag on atoms.** Rejected: same coupling problem — Brain's atoms
would carry Article-Pipeline-specific metadata.

**C — Logic inside Article Pipeline (chosen).** Brain stays a passive
source; Article Pipeline reads through a narrow, auditable channel (see
0022).

## Consequences

Brain remains unmodified by Article Pipeline. Reading happens through a
single defined channel rather than ad hoc filesystem access.

## Validation
Unverified — no automated check confirms Article Pipeline never writes
to Brain. This is an architectural intent, not a tested invariant.

## Reversal condition
None specified.

## Source
Explicit owner decision.
