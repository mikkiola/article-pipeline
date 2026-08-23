---
id: ADR-0033
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0033: Contributor Governance — Post-Merge Reconciliation via Existing Tier 2 Primitives

Relates to: ADR-0002 (tooltempest, Tier 2 doc-sync), ADR-0003 (tooltempest,
confirmation granularity)

## Status

Accepted

## Context & Constraints

The project currently has one contributor: the owner, working through
Claude Code sessions with direct access to `main`. The owner wants to
accept external contributions — both occasional pull requests and, at
later stages, recurring collaborators — without weakening two
guarantees already established for Tier 2:

- ADR-0002(b): `BACKLOG.md` and `ROADMAP.md` encode owner judgment
  (priority, completion status) and must never be written without the
  owner's explicit confirmation.
- The atomicity guarantee validated in Tier 2 Stage 3: a single
  `/doc-sync` invocation either applies all three target files or
  rolls all of them back — no invocation may leave the three documents
  partially applied relative to each other.

An initial design proposed a two-step GitHub Actions flow: a
post-merge step writes `ARCHITECTURE.md` directly, then a second,
independent step opens a separate pull request containing the
`BACKLOG.md`/`ROADMAP.md` diff. This does not violate ADR-0002(b) —
the gated files are never written without an explicit owner action —
but it introduces a failure mode Tier 2's atomicity guarantee does not
cover: the two steps are not one invocation, so `ARCHITECTURE.md`
could be written while the corresponding `BACKLOG.md`/`ROADMAP.md`
proposal is later abandoned, leaving `main` in a state ADR-0032's
Drift Warning exists specifically to catch.

## Decision

Post-merge reconciliation calls `apply_tier2_sync()` exactly once per
contributor pull request, for all three target files together,
reusing the existing snapshot, diff, and rollback primitives from
Tier 2 Stage 2 and Stage 3 unmodified. The GitHub Actions workflow
does not reimplement diff generation, file writes, or rollback logic.

1. **One invocation, not two independent steps.** The Post-Merge
   Action calls `doc_sync_tier2.py` once, with `proposed` covering all
   three files. `ARCHITECTURE.md` is written directly inside that same
   call (per ADR-0002b, unchanged). `BACKLOG.md`/`ROADMAP.md` changes
   are not written directly — the Action captures the diff
   `apply_tier2_sync()` would produce and stages it as the body of a
   new pull request.
2. **The reconciliation pull request is the confirmation gate**,
   replacing Stage 3's terminal `input()` prompt with a GitHub-native
   equivalent: merging the reconciliation PR is "accept"; closing it
   without merging is "reject."
3. **Reject triggers the same rollback path Stage 3 already
   guarantees.** If the reconciliation PR is closed without merging,
   an Action step calls `restore_snapshots()` against the snapshot
   captured at invocation start, reverting `ARCHITECTURE.md` in `main`
   to its pre-invocation state. This is the existing Stage 3 rollback
   path, triggered by a GitHub event (`pull_request.closed`,
   `merged == false`) instead of a rejected CLI prompt.
4. **Token scoping follows least-privilege, scope-zeroing GitHub
   Actions practice:** no top-level write permissions. The step that
   opens the reconciliation PR is scoped to `pull-requests: write`
   only. The step that runs on `pull_request.closed`/`merged == false`
   to roll back `ARCHITECTURE.md` is scoped to `contents: write` only,
   and only that step — no job in the workflow is scoped to merge
   authority over any pull request. Merge authority for the
   reconciliation PR remains with the owner (or a designated reviewer
   under a future multi-owner ADR), enforced through GitHub branch
   protection on `main`, not convention.
5. **Concurrent `docs/` changes are resolved by close-and-reopen, not
   in-place recalculation or blocking.** If `main` advances (another
   PR touching `docs/` merges) while a reconciliation PR is still
   open, the Action closes the stale reconciliation PR with an
   explanatory comment and opens a new one, computed fresh via the
   same `apply_tier2_sync()` call against current `main`. This reuses
   the existing snapshot-diff-apply primitive rather than introducing
   in-PR recalculation logic or a merge queue/lock on `docs/`, which
   would slow down contributors for the sake of a rare event.
6. **Reconciliation runs are logged the same way Tier 1 evidence
   records are** — the contributor's merged PR SHA, the reconciliation
   commit SHA (if merged), and outcome (applied / rejected-and-rolled-
   back / superseded-by-reopen). This preserves the audit trail
   without inventing a new record format.

## Alternatives & Rationale

| Option | Pros | Cons | Risks |
|---|---|---|---|
| A. Chosen: single `apply_tier2_sync()` call, PR-as-confirmation, close-and-reopen on staleness | Reuses tested atomicity guarantee unchanged; no new rollback logic; audit trail matches existing Tier 1 format; scope-zeroed tokens follow established least-privilege practice | Requires the Action to hold a narrowly-scoped write path to `main` for rollback only | Misconfigured Action permissions could widen beyond rollback-only; mitigated by explicit per-job `permissions:` blocks and branch protection, not convention alone |
| B. Two independent steps (direct-write `ARCHITECTURE.md`, then a separate unlinked PR) | Simpler Action logic | Partial-success state reachable if the second PR is abandoned; no cross-step atomicity | Reintroduces the exact drift ADR-0032 exists to catch |
| C. Fully automated merge, no owner confirmation for gated files | Zero owner interaction | Directly violates ADR-0002(b) | Rejected outright |
| D. In-place PR recalculation on every `docs/`-touching merge | Reconciliation PR is always live/current | New recalculation logic not covered by existing tests; PR content could change under the owner mid-review | Rejected: adds a class of behavior Stage 3 never validated |
| E. Block contributor merges while a reconciliation PR is open | Guarantees no staleness | Creates an artificial queue gated on owner responsiveness | Rejected: contradicts the goal of low-friction external contribution |

## Consequences

- No new core logic beyond the GitHub Actions workflow itself;
  `doc_sync_tier2.py`'s existing functions are called, not extended.
- The workflow requires per-job `permissions:` blocks (scope-zeroed,
  least-privilege) — this is a concrete implementation requirement,
  not a stated intent to configure later.
- Close-and-reopen is expected to be rare in practice (requires a
  second `docs/`-touching merge while a reconciliation PR is still
  open) but must be tested, not assumed rare and left unhandled.

## Confirmation & Revisit

The workflow must be tested against scenarios equivalent to Stage 3's
(clean apply via merge, rejection-rollback via PR close, invalid/
missing confirmation) adapted to GitHub events, plus the close-and-
reopen path under a simulated concurrent `docs/` merge.

If GitHub's event model proves unreliable for triggering rollback on
PR close (a `closed`/`merged == false` event is missed or delayed), or
if branch protection cannot reliably enforce merge-only access to the
gated documents, revisit this ADR — do not patch with a manual
fallback that quietly reintroduces Option B's partial-success risk.

**Source.** Architect chat session, 2026-08-19. Governance design discussed prior
to Tier 2 code implementation completion; informed by GitHub Actions
least-privilege token practice (scope-zeroing permissions model) and
this project's own `decision-analysis` skill applied to the
concurrent-PR question.
