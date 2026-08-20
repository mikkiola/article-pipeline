# ADR-0035: Pre-Merge Gate for Gated Docs — Replaces ADR-0033 Points 2/3

Status: Accepted
Relates to: ADR-0033 (article-pipeline, contributor governance —
post-merge reconciliation) — **partially superseded**: this ADR
supersedes ADR-0033 points 2 ("the reconciliation pull request is the
confirmation gate") and 3 ("reject triggers rollback") only. Points 1
("one invocation, not two independent steps"), 4 ("token scoping"), 5
("close-and-reopen"), and 6 ("evidence logging") remain in effect,
with point 4 simplified per this ADR's Consequences. ADR-0033 itself
is not edited, per Immutable Lineage (ADR-0011) — its Status line
still reads Accepted, and its points 2/3 remain in its text
unmodified as a historical record of the design this ADR replaces.
Also relates to ADR-0034 (article-pipeline, contributor-supplied doc
updates) — the decision that exposed the gap this ADR closes.

**A note on this repo's ADR discipline.** Every prior use of
"superseded" in `docs/adr/` (e.g., ADR-0002, marked "SUPERSEDED by
0004" in full) has been whole-document supersession — an entire ADR
replaced by another. This ADR is different: it supersedes two
specific numbered points inside ADR-0033 while the rest of that ADR
remains in force. This is a new pattern for this repository, not
previously used, and is called out explicitly here rather than
silently introduced. `docs/CONSTITUTION.md`'s ADR-discipline section
("a changed decision becomes a new ADR that supersedes the old one")
is written in whole-ADR terms; this ADR is the first instance where
that language needs a point-level reading. No change to
`docs/CONSTITUTION.md` is made as part of this ADR — flagging the gap
is in scope, resolving it is not.

## Context

Attempting to actually build the workflow implementing ADR-0033
points 1–4 (this session, Part B second slice) surfaced a structural
problem in points 2 and 3 that neither ADR-0033 nor ADR-0034
anticipated: under ADR-0034, a contributor supplies
`BACKLOG.md`/`ROADMAP.md` content directly in their own pull request,
and that PR merges to `main` through GitHub's ordinary merge
mechanism — before any post-merge automation ever runs. By the time a
post-merge reconciliation workflow computes a diff against current
`main`, `main`'s `BACKLOG.md`/`ROADMAP.md` content already **is** the
proposed content; the diff is always empty, and a PR proposing "change
main to what main already contains" is structurally a no-op. ADR-0033
point 5 confirms this was never the intended model — it describes the
reconciliation diff as "computed fresh via the same
`apply_tier2_sync()` call against current `main`," which only makes
sense if `main` does **not** yet hold the gated docs' proposed content
at reconciliation time. Combined with ADR-0034, that precondition no
longer holds.

This is not a defect specific to this project's implementation. It is
an instance of a known architectural pattern — gating a mutation
**after** the mutation has already landed (sometimes described as a
"post-hoc gate," or, by analogy to the check-then-act race in
TOCTOU — time-of-check to time-of-use — bugs, a pipeline where the
"check" step runs after the "use" step it was meant to precede). Three
independent external architectural reviews conducted this session,
given the same facts, converged unanimously on both the diagnosis
(gate-after-mutation) and the standard fix: move the gate **before**
the mutation, using the platform's native pre-merge review mechanism
(GitHub CODEOWNERS plus branch protection) rather than trying to gate
the mutation's *effect* after the fact.

## Decision

`docs/BACKLOG.md` and `docs/ROADMAP.md` become CODEOWNERS-protected
paths. Branch protection on `main` requires an owner (or a designated
reviewer, per ADR-0033 point 4's already-anticipated future
multi-owner case) to approve any pull request touching those two
paths before it can merge. The contributor's original PR review *is*
the confirmation gate for gated docs — no separate post-merge
reconciliation PR exists for `BACKLOG.md`/`ROADMAP.md`.
`docs/ARCHITECTURE.md` is unaffected by this decision: it remains
ungated per ADR-0002(b) and is still written directly by post-merge
automation per ADR-0033 point 1 and ADR-0034 — that mechanism has no
analogous no-op problem, since ARCHITECTURE.md was never meant to
require a separate confirmation step in the first place.

## Options considered

| Option | Pros | Cons | Risks |
|---|---|---|---|
| A. Chosen: pre-merge gate via CODEOWNERS + branch protection on `BACKLOG.md`/`ROADMAP.md` | Native GitHub mechanism, no custom workflow logic; gate runs before the mutation, so it can actually block something; adds no new persistent infrastructure | Requires a real repo-settings configuration step (branch protection), not just a code change | Misconfigured branch protection could fail to actually enforce the required review — must be verified in GitHub's settings, not just asserted |
| B. Separate proposal from canonical artifact — contributors submit intent/metadata about doc changes rather than the gated file content directly, with actual `BACKLOG.md`/`ROADMAP.md` text generated by a later, confirmed step | Content generation stays fully removed from the contributor's direct write | Reopens ADR-0034's already-closed authorship question for these two files specifically — trades one resolved decision for a new open one | Rejected: undoes recent, deliberate work (ADR-0034, `CONTRIBUTING.md`) without a stronger reason than avoiding a repo-settings step |
| C. Gate a downstream effect rather than the merged content itself — e.g., a persistent staging branch that lags `main`, with contributor PRs landing there first and a separate, confirmed sync promoting `BACKLOG.md`/`ROADMAP.md` changes to `main` | Keeps confirmation entirely inside custom workflow logic, no GitHub settings dependency | Adds a persistent branch and a promotion mechanism ADR-0033/0034 never described; new failure modes (staging/main drift) | Rejected: introduces infrastructure not otherwise needed to solve a problem GitHub's native review gate already solves |

## Chosen

A.

## Why

Option A is the only one that doesn't reopen a decision this project
already closed deliberately (ADR-0034's contributor-authorship model)
and doesn't add new persistent infrastructure (a staging branch, Option
C) to solve a problem GitHub's own pre-merge review mechanism already
solves natively. Path-based required review via CODEOWNERS and branch
protection is standard, well-precedented practice for exactly this
class of problem — protecting specific paths that encode
higher-trust judgment within an otherwise open contribution model —
which is what the external reviews gathered this session converged on
independently of each other.

## Constraints

This ADR does not change ADR-0034: gated-doc content is still
contributor-authored, in the contributor's own PR. It does not affect
`ARCHITECTURE.md`'s write path (ADR-0033 point 1 / ADR-0034,
unchanged). It requires GitHub branch protection settings to actually
be configured in the repository — a real deployment/administration
step, not something a commit alone accomplishes; the `CODEOWNERS` file
this ADR introduces has no enforcement effect on its own until branch
protection is turned on and configured to require review from code
owners on the protected paths.

## Rejected

B — rejected because it reopens ADR-0034's authorship decision for
`BACKLOG.md`/`ROADMAP.md` specifically, trading a resolved question
for a new open one, without a reason strong enough to justify undoing
recent, deliberate work. C — rejected because it introduces a
persistent staging branch and promotion mechanism not otherwise
needed, when GitHub's native pre-merge review gate already addresses
the same problem without new infrastructure.

## Consequences

- ADR-0033 point 4 (scope-zeroed per-job token permissions) simplifies
  substantially: there is no reconciliation-PR-opening job (no
  `pull-requests: write` scope needed for that purpose), and no
  PR-close rollback-trigger job scoped to `contents: write` for
  reverting a post-merge gated-doc mutation, because no post-merge
  mutation of `BACKLOG.md`/`ROADMAP.md` exists to roll back anymore.
  This removes most of what points 2/3/4 were going to require the
  workflow to build in the prior slice.
- If a merged PR's `ARCHITECTURE.md` change is later found wrong, its
  correction is an ordinary revert PR, not ADR-0033's rollback
  mechanism (`restore_snapshots()` triggered by a reconciliation PR
  close) — that mechanism was specific to the now-removed gated-doc
  confirmation flow.
- The workflow implementation still needed for ADR-0033 going forward
  is narrower than previously scoped: point 1's two-call mechanic
  (writing `ARCHITECTURE.md` only — there is no longer a gated-doc
  diff-capture-for-a-reconciliation-PR half of that step), a
  `CODEOWNERS` file (this ADR introduces it), and branch protection
  configuration (a manual GitHub settings step, not implementable in a
  commit).

## Validation

Whether branch protection actually blocks a PR touching
`BACKLOG.md`/`ROADMAP.md` without the required owner/code-owner
approval must be manually verified in GitHub's repository settings
once configured — this ADR does not itself verify that, since the
configuration step is out of this session's scope (see
`docs/BACKLOG.md`). Recorded here as an open verification step, not
assumed to work by virtue of the `CODEOWNERS` file existing.

## Reversal condition

If CODEOWNERS-based path protection proves insufficient — for example,
GitHub's permissions model can't express a needed granularity, or a
future multi-reviewer setup requires more nuance than a single
required approval — revisit this ADR.

## Source

Architect chat session, 2026-08-19. Three independent external AI
architectural reviews, given this session's finding-unknowns BLOCKING
result from the Part B second slice, converged unanimously on the
gate-after-mutation / TOCTOU-adjacent-pipeline-conflict diagnosis and
on CODEOWNERS + branch protection as the standard resolution.
