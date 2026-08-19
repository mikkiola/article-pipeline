# ADR-0032: ToolTempest Drift Warning (pre-push check)

<!--
  REPOSITORY: mikkiola/article-pipeline (docs/adr/0032-drift-warning.md),
  NOT tooltempest. This check is article-pipeline-specific orchestration
  (comparing THIS repo's .tooltempest.lock against ToolTempest's
  origin/main) -- it lives in article-pipeline's own tracked hook source
  (scripts/hooks/pre-push), not in ToolTempest's client-agnostic
  doc_sync.py. See Rationale for why this placement was chosen over the
  alternative.

  Number: article-pipeline's docs/adr/ sequence -- 0031 is the last
  known occupied number in this repo (D-025 paired experiment, unrelated
  to this ADR), so 0032 is next. This is a DIFFERENT sequence from
  ToolTempest's (currently 0001, 0002) -- the two repos' ADR numbering
  is independent, not shared. Do not confuse the two; conflating them
  was an error already caught and corrected once this session (see
  ADR-0002's own history in ToolTempest). Re-check `ls docs/adr/` in
  article-pipeline immediately before commit -- do not assume 0032 is
  still free if time has passed since this draft was written.
-->

## Status

Accepted — implemented and regression-tested (2026-08-19), commit
404c24c93a0edbc1a83d4e078a7bb6ec2ba99f79.

## Context

ToolTempest fixes reach article-pipeline only through a manual resync
step (`scripts/sync-tooling.sh`, which updates `.tooltempest.lock` and
pulls the pinned commit's vendored files). This session alone hit the
same gap three separate times: a fix landed and was pushed in
ToolTempest, but article-pipeline kept running the pre-fix vendored
copy until someone noticed and ran the resync manually. Each time, the
gap was caught only because the architect or Claude Code happened to
notice mid-session, not because anything enforced it.

With ToolTempest's current single consumer (article-pipeline), a
missed resync is inconvenient but visible quickly, since it's the
owner's only active project. As more consumers connect (2-3 realistically
expected within the next few months, per the owner's roadmap), the
same gap becomes silent divergence with no built-in visibility into
which consumer is running which version.

Three candidate mechanisms were considered for surfacing this drift
automatically, discussed in the architect chat:
A. Check at `pre-commit` (runs on every local commit).
B. A separate command run on demand (`sync-tooling.sh --check`).
C. Check at `pre-push` (runs when pushing to a remote).

## Decision

Implemented **C: check at pre-push.**

The check reads the pinned commit from `.tooltempest.lock`, runs
`git ls-remote <repository-url-from-the-lock-file> main` to get
ToolTempest's current `origin/main` tip without a full fetch, and
compares the two SHAs. If they diverge, it prints a warning naming
both short SHAs and pointing at `scripts/sync-tooling.sh`. It never
blocks the push -- this is an informational check, not a validation
gate. If the `git ls-remote` call itself fails (no network, host
unreachable, anything), the check fails silently: no crash, no
warning about the check itself, and the push proceeds normally.

## Rationale

**Why pre-push, not pre-commit (rejected Option A):** `pre-commit`
fires on every local commit -- the most frequent, most
latency-sensitive git operation -- and must stay instant and
offline-safe. Adding a network call there would either slow down every
commit or produce confusing behavior when offline (unclear whether
"no warning" means "no drift" or "the check itself couldn't run").
`pre-push` is the point where network access is already guaranteed --
the author is about to send data to GitHub regardless -- so checking
for drift there reuses a connection the operation already requires,
adding no new dependency. The warning surfaces slightly later than a
commit-time check would (at push, not at the local commit), which is
an accepted trade-off, not a gap: push is also the natural moment to
notice drift, since it's when the author is about to share this state
externally anyway.

**Why not a separate on-demand command (rejected Option B):** the
owner explicitly identified their own failure mode for this option
during the architect-chat discussion: a command that must be
remembered and run manually solves nothing if it's the remembering
itself that fails. This is the same category of gap the check exists
to close in the first place -- a mechanism that depends on not
forgetting is not a fix for "we keep forgetting."

**Why warn instead of block:** blocking the push on drift would turn
an informational signal into a hard dependency on ToolTempest's GitHub
availability at push time, and would stop the author's actual work
(pushing their own article-pipeline change) over a condition unrelated
to that change's correctness. The existing component/ARCHITECTURE.md
pairing check in the same hook already establishes a warn-only pattern
for this class of concern; this check follows it rather than
introducing a second enforcement style in the same file.

**Why silent on the happy path:** a "you're up to date" line on every
single push would be noise the author tunes out within a day,
defeating the purpose of a warning that's supposed to stand out when
it actually matters.

**Why it lives in article-pipeline's scripts/hooks/pre-push, not
ToolTempest's doc_sync.py:** `doc_sync.py` documents itself as
client-agnostic, carrying no project- or domain-specific logic. This
check is inherently article-pipeline-specific -- it compares this
repository's own lock file against a specific upstream. Placing it in
article-pipeline's own git-tracked hook source means future edits or
fixes to this check don't require a ToolTempest push-and-resync cycle
to land; it can be iterated on directly. The file already contained an
established warn-only pattern (the component/ARCHITECTURE.md pairing
check) for this check to sit alongside.

## Scope / Invariants

- Never blocks a push. A failed drift check (network failure, bad URL)
  and a successfully-detected real divergence are both non-fatal to
  the push; only the latter prints anything.
- Runs only at pre-push, not pre-commit or any other hook.
- Reuses the repository URL already stored in `.tooltempest.lock` --
  no second hardcoded copy of the URL.
- Silent when the pinned commit matches `origin/main`'s current tip.

## Implementation Constraints

- `git ls-remote <url> main` only -- no full fetch, no clone.
- Failure of the `git ls-remote` call itself is absorbed (`|| true`
  under `set -euo pipefail`) and produces no output and no error --
  distinguishing "check couldn't run" from "no drift found" is
  explicitly not surfaced to the author, since neither case should
  interrupt or alarm them.
- Short-SHA display (7 characters) in the warning, matching this
  session's existing convention in commit messages and hook output.

## Rejected Options

- **Option A (pre-commit):** rejected -- see Rationale. Network calls
  don't belong on the highest-frequency git operation.
- **Option B (separate on-demand command):** rejected -- see
  Rationale. Depends on remembering to run it, which is the exact
  failure mode it would exist to prevent.

## Consequences

- The author now gets a signal, without needing to remember to check
  manually, when their local ToolTempest pin is behind. They still
  have to act on it themselves (run `scripts/sync-tooling.sh`) -- this
  ADR does not implement semi-automatic resync (e.g., a bot opening a
  PR on drift), which remains a separate, undecided question noted in
  docs/BACKLOG.md's `[TOOLTEMPEST]` CI entry.
- This does not address the underlying risk that motivated it as
  strongly as CI would (a bad fix landing in ToolTempest before any
  consumer notices) -- Drift Warning tells a consumer they're behind,
  it does not verify whether being caught up is actually safe. CI
  (tracked separately in docs/BACKLOG.md) is the complementary
  mechanism that catches a bad fix at the source, before any consumer
  -- warned or not -- could pull it.
- **This mechanism does not propagate to new ToolTempest consumers
  automatically.** Because it lives in article-pipeline's own
  scripts/hooks/pre-push rather than in ToolTempest's client-agnostic
  doc_sync.py, a new project connecting to ToolTempest gets none of
  this protection by default -- it would need to copy this same
  pattern (a drift check comparing its own .tooltempest.lock against
  ToolTempest's origin/main) into its own pre-push hook independently.
  This is the same class of "we'll forget" risk this ADR exists to
  close, one level up: as ToolTempest gains consumers, remembering to
  replicate this check into each new one is itself an unenforced
  manual step. Worth deciding, when the second consumer is actually
  being onboarded, whether this check should instead move into
  ToolTempest itself as an opt-in helper script consumers can pull in
  -- not decided here, flagged as a known limitation of this ADR's
  scope.

## Reversal Condition

If `git ls-remote` calls at pre-push time turn out to meaningfully
slow down pushes in practice (e.g., on unreliable networks where the
call hangs rather than failing fast), or if the warning is
consistently ignored once several consumers exist (suggesting
pre-push visibility isn't sufficient and a stronger mechanism, like
semi-automatic PR-based resync, is needed), that is grounds to revisit
-- via a new, superseding ADR, not an edit to this one.

## Validation

Regression-tested against real article-pipeline (not a scratch clone;
`.tooltempest.lock` restored to its correct committed value after each
test):
1. Lock pinned at current `origin/main` tip -- silent, exit 0.
2. Lock deliberately pinned at an older commit (b66de81, one of this
   session's own earlier ToolTempest commits) -- warning printed with
   correct short SHAs (`b66de81` / `43549a6`), push still exits 0.
3. Unreachable repository URL -- check fails silently, no crash, no
   block, exit 0, no hang (full hook run completed in under 2 seconds).

## Source

Session: DocOps Protocol V2.0 hardening + Tier 2 /doc-sync
architecture, 2026-08-19. Mechanism choice (pre-push over pre-commit
or a separate command) decided in the architect chat, recorded in
article-pipeline's docs/BACKLOG.md (`[TOOLTEMPEST]` CI entry, commit
16b87d0) prior to implementation. Implemented and verified by Claude
Code, commit 404c24c93a0edbc1a83d4e078a7bb6ec2ba99f79. Number 0032
confirmed against article-pipeline's docs/adr/ (0031 last known
occupied, D-025 experiment, unrelated) at draft time -- re-verify at
commit time.
