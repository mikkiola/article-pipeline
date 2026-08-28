---
id: ADR-0041
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0041: Mechanical Verification Scope — Document-Format Conventions Only

## Status

Accepted

## Context & Constraints

`[B-041]` (`docs/BACKLOG.md`) found that `docs/CONSTITUTION.md` states
many prescriptive rules, but only one — the ADR-citation rule
(`scripts/check-adr-citation.sh`, wired into `scripts/hooks/pre-push`)
— is actually backed by a mechanical check. A same-session fact
inventory (`docs/spec-prep/B-040-B-041-facts.md`, since deleted per
this ADR's own closing task — full text retained in git history)
counted 10 representative rules: 1 mechanically enforced, 1 names a
real script (`scripts/check_manifest.py`) that exists but isn't wired
into any hook, 8 with no corresponding script anywhere in `scripts/`.

A `phrase-decomposer` sensor run flagged a BLOCKING semantic fork
before this could be resolved: "format/structural requirement" (the
term `[B-041]`'s own title used) admits a narrow reading
(document-content conventions — headings, IDs, citation patterns,
field presence, the same category as the existing ADR-citation
precedent) and a broad reading (any prescriptive `docs/CONSTITUTION.md`
statement, including judgment-based/behavioral/process rules like the
TDD threshold or the "verify no existing coverage" search obligation).
The two readings lead to materially different scopes of future work —
narrow bounds a future `/spec` to extending an existing pattern; broad
would require designing a tiered enforcement taxonomy for a
heterogeneous rule set.

External research (3 independent AI passes, gathered during the same
fact-inventory pass) converged on a "Fitness Functions"/tiered-
enforcement pattern as one answer to the broad reading, with one
dissenting "delete unenforceable rules" position — both are answers to
a branch this decision does not take (see Alternatives below).

## Decision

Mechanical enforcement in this project covers only document-format
conventions a script can cheaply and deterministically verify —
headings, stable IDs, citation patterns, required-field presence — the
same category the existing ADR-citation check already represents.
Judgment-based, behavioral, or process rules (e.g. the TDD threshold,
"verify no existing component covers this responsibility," the
codebase-wide-search-before-certain-diffs rule, the sensitive-ops
execution-environment rule) are explicitly not candidates for
mechanical enforcement, in principle — not merely unenforced today for
lack of tooling.

Recorded in `docs/CONSTITUTION.md`'s new "Mechanical verification
scope" section.

## Alternatives & Rationale

**A. Broad — any prescriptive `docs/CONSTITUTION.md` statement is a
mechanical-enforcement candidate.** Rejected. Would require inventing
a tiered enforcement taxonomy (per the external "Fitness
Functions"/baseline-and-ratchet research) to classify a fundamentally
heterogeneous rule set — real cost, uncertain payoff, and in tension
with this project's own existing token/cost-consciousness principle:
automating what can't actually be automated cheaply spends effort
without reducing risk, and misrepresents a judgment call as a
checkable fact.

**B. Chosen — narrow, document-format conventions only.** Matches the
one mechanism already proven to work (the ADR-citation check) and the
owner's own stated reasoning: *"у нас есть правило токенов и затрат,
логично что проверяем только то что легко проверяется... автоматизация
автоматизирует только то что можно автоматизировать"* (cost-
consciousness is already an established principle; automate only what
is actually automatable). Consistent with `docs/ROADMAP.md`'s own
Current-pointer rule against forcing an advisory/judgment sentence into
a table cell — the same reasoning applied to code enforcement instead
of document formatting: don't force a human/agent judgment call to
pretend to be a deterministic check.

## Consequences

- `docs/CONSTITUTION.md` gains a standalone "Mechanical verification
  scope" principle, generalizing from the existing ADR-citation
  precedent rather than leaving it as an unexplained one-off.
- The 8 currently-unenforced, judgment-based rules found in the
  `[B-041]` inventory (TDD threshold, "verify no existing coverage,"
  search-before-diff, sensitive-ops environment, etc.) are now
  explicitly classified as out-of-scope for mechanical enforcement —
  a closed question, not an open gap awaiting a future script.
- `scripts/check_manifest.py`'s named-but-unwired status (found in the
  same inventory) remains a separate, still-open question — this ADR
  does not resolve whether it should be wired into a hook; that is a
  ToolTempest-consumer-obligation mechanics question, not a
  scope-of-enforcement question.
- A future `/spec` interview proposing a new mechanical check can cite
  this ADR to confirm the proposal is in-scope (document-format)
  before investing interview time, rather than re-litigating the
  narrow/broad question each time.

## Confirmation & Revisit

Confirmed by construction: this decision closes `[B-041]`'s
`phrase-decomposer` BLOCKING finding exactly as the owner resolved it
on 2026-08-25 (originally recorded in
`docs/spec-prep/B-040-B-041-facts.md`'s "Open decisions" section; full
text preserved above in this ADR's Context/Alternatives, and in
`docs/BACKLOG.md`'s `[B-041]` closure note, before that spec-prep file
was deleted).

Revisit if a future session finds a judgment-based rule that turns out
to have a cheap, deterministic proxy after all (the same way
`scripts/check-doc-pairing.sh` is a coarse-but-real proxy for "doc
updated in step with a component change") — that would be a new,
narrower ADR extending this one's scope for that specific rule, not a
reason to reopen the broad-vs-narrow question generally.

**Source.** `[B-041]`'s `phrase-decomposer` BLOCKING finding,
2026-08-24 (Metadata/ID Layer `/spec` interview's closing independence
check); owner's narrow-scope resolution, 2026-08-25 (recorded in
`docs/spec-prep/B-040-B-041-facts.md`, cross-checked against 3
independent AI research passes on the broad-reading alternative).
Formalized as this ADR and the `docs/CONSTITUTION.md` section it
records, 2026-08-28, closing `docs/BACKLOG.md`'s `[B-041]`.
