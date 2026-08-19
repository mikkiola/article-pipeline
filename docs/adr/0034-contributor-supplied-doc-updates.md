# ADR-0034: Contributor-Supplied Doc Updates — Source of `proposed` Content for ADR-0033's Workflow

Status: Accepted
Relates to: ADR-0033 (article-pipeline, contributor governance —
post-merge reconciliation), ADR-0002/ADR-0003 (tooltempest, Tier 2
doc-sync). Extends ADR-0033 without editing it, per Immutable Lineage
(ADR-0011).

## Context

ADR-0033 specifies that post-merge reconciliation calls
`apply_tier2_sync()` with `proposed` covering all three Tier 2 target
files (`ARCHITECTURE.md`, `BACKLOG.md`, `ROADMAP.md`), reusing the
existing snapshot/diff/rollback primitives. It never states where
`proposed`'s content — the actual new text for each file — originates
for a contributor-PR-triggered run. In the pre-ADR-0033 flow, that
content is authored by "the agent" (Claude Code, in an interactive
session) deciding by its own judgment that a milestone has closed, per
tooltempest ADR-0002(c): "The agent decides autonomously when a
milestone has closed and invokes `/doc-sync` itself." No such session
runs inside a GitHub Actions job triggered by an arbitrary contributor
merge, so this judgment step has no defined owner in ADR-0033's
design. This gap was found during this session's Part B implementation
attempt (finding-unknowns sensor, BLOCKING) and is recorded, with
reasoning, in `docs/BACKLOG.md`'s "P1 — Implement ADR-0033's GitHub
Actions workflow" entry, "Decision (owner, 2026-08-19)" paragraph.

Separately, the same investigation found a second fact that affects
how the workflow can call the Tier 2 primitives at all:
`apply_tier2_sync(interactive=False)` does not skip
`BACKLOG.md`/`ROADMAP.md` when they appear in `proposed` — it raises
`RuntimeError` immediately, before any snapshot or diff is produced,
if `proposed` contains any `GATED_DOCS` key
(`scripts/doc_sync_tier2.py:205-213`, verified directly against
source). A single non-interactive call passing all three files
together, as ADR-0033 point 1's prose literally describes, is
therefore not achievable as written. The workflow this ADR's decision
enables will need two calls to the exposed primitives within one job
step: `apply_tier2_sync()` for `ARCHITECTURE.md` alone
(`interactive=False`, no `GATED_DOCS` key present, so no
`RuntimeError`), and `snapshot_tier2_docs()` /
`build_document_diffs()` called directly for the
`BACKLOG.md`/`ROADMAP.md` diff, without writing anything. Both
functions are part of `doc_sync_tier2.py`'s public `__all__`, so this
reuses the same unmodified primitives ADR-0033 requires — it does not
reimplement diff generation, file writes, or rollback logic. This ADR
records the content-source decision; the two-call mechanic itself is
Part B implementation detail, not re-litigated here.

## Decision

Contributors supply their own doc updates
(`ARCHITECTURE.md`/`BACKLOG.md`/`ROADMAP.md`) within their own pull
request, per a documented contribution requirement (a separate,
not-yet-written `CONTRIBUTING.md` task, BACKLOG.md's second checkbox
under this entry). The reconciliation Action re-reads the merged PR's
tree as `proposed` content rather than generating it — no automated
content generation of any kind runs inside the Action.

For `ARCHITECTURE.md`, this changes what ADR-0033 point 1's "written
directly inside that same call" means in practice: the file's new
content is already the one the contributor's merge committed to the
tree, so `apply_tier2_sync()`'s direct write becomes an effective
re-write of content that already exists on disk, not new content
generation. This does not contradict ADR-0033 point 1 — the call
still happens, still writes directly, still requires no confirmation
— it clarifies what "direct write" produces when the input source is
the contributor's own commit rather than freshly authored text.

## Options considered

| Option | Pros | Cons | Risks |
|---|---|---|---|
| A. Chosen: contributor supplies doc updates in their own PR; Action re-reads the merged tree | No new content-generation dependency; reuses existing human judgment (the contributor's) rather than inventing an automated substitute; keeps the Action's job strictly to confirmation/atomicity mechanics, matching ADR-0033's own scope | Makes a `CONTRIBUTING.md` requirement load-bearing, not just a style nicety — a contributor who skips or gets the doc updates wrong breaks the reconciliation flow, not just review comments | Tier 1's existing pre-commit/pre-push `doc_sync.py` validation may or may not already catch a PR missing required doc updates — unverified, tracked as this entry's third BACKLOG checkbox, not resolved by this ADR |
| B. An LLM call inside the Action drafts doc updates from the merged PR's diff | No contribution-process burden on external contributors | New dependency (API key/secret, prompt, cost) and a new failure surface, introduced on the project's most protected documents (`BACKLOG.md`/`ROADMAP.md` encode owner judgment per ADR-0002b) | Rejected: trades a documentation-process requirement for an unreviewed automated writer on gated, judgment-encoding files |
| C. A revived rule-based diff classifier (`doc_impact.py`-style) infers doc updates from the code diff | Fully automated, no contributor burden | This exact approach was already built in this repo (`scripts/doc_impact.py`, commit `2e3f982`) and explicitly abandoned one commit later (`a8487c4`, "too conservative, wrong scope") | Rejected: reintroduces an approach this project already tried and discarded, for the same reasons that led to its removal |
| D. The owner manually supplies `proposed` per PR | No contributor-facing requirement to define or enforce | Reintroduces a manual step per contributor PR, defeating the purpose of an automated reconciliation workflow | Rejected: adds a manual bottleneck this decision exists to avoid |

## Chosen

A.

## Why

Option A is the only one that avoids inventing a new automated
authority over `BACKLOG.md`/`ROADMAP.md` content (which ADR-0002(b)
reserves for explicit human judgment) while still keeping the
reconciliation Action's own logic limited to confirmation/atomicity
mechanics, matching ADR-0033's stated scope ("does not reimplement
diff generation, file writes, or rollback logic"). It reuses the
existing human-judgment model (a person — the contributor —
authoring the actual text) rather than substituting a new, unproven
automated one, and it does not resurrect an approach (Option C) this
project already built and explicitly rejected for being the wrong
shape of solution.

## Constraints

This ADR does not resolve what Tier 1's existing `doc_sync.py`
pre-commit/pre-push validation currently checks with respect to a PR
missing required doc updates — that is BACKLOG.md's third checkbox
under this entry, open and unresolved here. It does not write the
`CONTRIBUTING.md` requirement itself — that is BACKLOG.md's second
checkbox, a separate task. It does not resume or complete Part B's
GitHub Actions workflow implementation; it only unblocks it by
answering the one question that was blocking it.

## Rejected

B — rejected because it introduces a new, unreviewed automated writer
(cost, credentials, and failure surface) over the project's most
protected documents, where ADR-0002(b) specifically reserves that
judgment for explicit human confirmation. C — rejected because this
exact mechanism was already implemented and explicitly abandoned in
this repository (commit `a8487c4`, "too conservative, wrong scope");
reviving it now would reintroduce a design already found unsuitable,
not a new idea. D — rejected because it reintroduces a manual
per-PR bottleneck that defeats the purpose of automating
reconciliation in the first place.

## Consequences

- A `CONTRIBUTING.md` requirement (BACKLOG.md's second checkbox under
  this entry) becomes load-bearing infrastructure, not a style
  preference: a contributor PR that omits or mis-formats the required
  doc updates will produce an incorrect or empty `proposed` payload
  when the Action re-reads the merged tree, not just a review
  comment.
- Whether Tier 1's existing `doc_sync.py` pre-commit/pre-push
  validation already flags a PR missing required doc updates is
  unverified (BACKLOG.md's third checkbox under this entry, still
  open) — this ADR's reliability depends on that question being
  answered and, if it's a gap, closed. This ADR does not resolve it.
- Part B's GitHub Actions workflow implementation can resume using
  this ADR's answer: `proposed` is assembled from the merged PR's
  tree contents for the three Tier 2 files, not generated by the
  Action.

## Validation

How this decision is tested is deferred to Part B's own workflow
implementation and its testing task (ADR-0033's Validation section,
and this repo's BACKLOG.md "Testing per ADR-0033's Validation section"
checkbox) — no test scenarios are specified here.

## Reversal condition

If contributors frequently submit PRs with incorrect or missing doc
updates despite the `CONTRIBUTING.md` requirement — making the
reconciliation-PR mechanism unreliable in practice — revisit this
ADR.

## Source

Architect chat session, 2026-08-19. Part B workflow implementation
investigation (finding-unknowns sensor, BLOCKING outcome) and the
owner's resulting decision, recorded in `docs/BACKLOG.md`'s
"P1 — Implement ADR-0033's GitHub Actions workflow" entry
(commit `a59f081`).
