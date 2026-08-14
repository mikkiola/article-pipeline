# 0020 — Claim extraction rules A/B/C (fact/hypothesis, detection vs. filling, personal beliefs)

## Status
ACTIVE, baseline. One of the few decisions with a full cycle including
an explicit counter-hypothesis test.

## Decision
Three rules: citability is necessary but not sufficient for a FACT tag;
detection and filling are handled as separate steps; grammatical person
is not a rejection criterion.

## Options
A — leave the original extraction behavior unchanged. B — introduce
rules A/B/C to correct the three specific failure modes observed
(chosen).

## Chosen
B.

## Why
The first Claim Extraction pilot run systematically failed in three
specific, identifiable ways: `basis` tagged as FACT when it was actually
a logical inference; claims assigned `no_claim` due to incomplete fields
rather than genuine absence of a claim; personal beliefs discarded based
on grammatical person rather than content. Each failure had a distinct,
fixable cause, so three targeted rules were introduced rather than one
broad behavioral change.

## Constraints
Rule application must remain iterative and testable against new atom
samples, not treated as fixed after one pass.

## Rejected
A — the original behavior was already shown to fail in three specific,
identifiable ways; leaving it unchanged would repeat those failures.

## Consequences
Implemented in `claim_extraction/extraction_rules.md`, applied across
four iterations on 13 atoms.

## Validation
Confirmed — the hypothesis "0/40 FACT tags is a property of the graph
itself" was explicitly tested and disproven on an independent sample of
5 new atoms (1/24 shown to be achievable, rare but real).

## Reversal condition
None specified.

## Source
Four rounds of manual owner verification, plus two independent AI
reviews.
