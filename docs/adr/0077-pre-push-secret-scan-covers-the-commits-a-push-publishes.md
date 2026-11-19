---
id: ADR-0077
status: Accepted
supersedes: null
superseded_by: null
source_type: inferred
---

# ADR-0077: The pre-push secret scan covers the commits a push publishes

## Status

Accepted on 2026-11-19. The policy and the known limits below are the Owner's
decisions. Decision point 3 and the limits 7 and 8 were extended the same day,
before this record reached `main`, at the Owner's instruction, after the scan
was found to pass under `GIT_TRACE` (Context). The supersession is partial (DR-6) and names one point of ADR-0038:
the scan that its Decision names, "the existing `gitleaks detect --source . --no-git -v`
call already in `scripts/hooks/pre-push`", and the statements that follow from
that scan mode (that it reads the raw filesystem and does not respect
`.gitignore`). In force, unchanged: ADR-0038's `local-fs-path` rule, its
allowlist in `.gitleaks.toml`, and the placement at pre-push. The frontmatter
fields stay null, following ADR-0076; ADR-0038 is not edited.

## Context & Constraints

Observation at `d365906`: `git show d365906:scripts/hooks/pre-push | sed -n 39,48p`
prints the scan: `gitleaks detect --source . --no-git -v --redact` when gitleaks
is installed, and the line "WARNING: gitleaks not installed, skipping secret scan."
otherwise. That call reads the files on disk. A secret that one pushed commit adds
and a later commit of the same push removes is not on disk, so the push publishes
it unscanned. Run on the hook of `d365906` in a throwaway clone with a fake secret
and a local bare remote, that push exited 0 with "no leaks found" (not reproducible
from this repository: the hook tests are not committed). A missing scanner lets the
push through.

Second observation, at `8a1e38e`, by real `git push` to a local bare remote: with
`GIT_TRACE=1` (also `GIT_TRACE2=1`, `GIT_TRACE_PERFORMANCE=1` and others) the
add-then-remove push exited 0 and the secret was published. Established: gitleaks
ends its scan on the first byte its own `git log` call writes to stderr, logs
`ERR error="stderr is not empty"`, reports "0 commits scanned", "no leaks found"
and exits 0. A git warning on stderr (an unreadable `core.attributesFile`) gives
the same result. Not established: whether gitleaks swallows other errors the same
way.

Constraints: the hook makes no network call (ADR-0072, point 2). Skipping the hook
with `--no-verify` is the Owner's action. The scan output prints no secret value.
The scanner stays gitleaks (`gitleaks version` prints 8.30.1 on the machine that
ran the checks).

## Decision

The pre-push hook scans, with gitleaks, the commits that the push makes reachable
on the remote, ref by ref. The working tree is not scanned and is not evidence.

1. Range. An updated ref, including a force push: the commits from the remote tip
   that git passes to the hook up to the pushed tip. A new ref: the commits of the
   pushed tip that no remote-tracking ref of that remote reaches. A deleted ref:
   nothing to scan. A merge commit is scanned for what the merge itself adds.
2. Published history is not rescanned.
3. The hook blocks the push when the scanner finds a secret, and when the scan
   cannot complete: the scanner is missing or fails, git fails or lacks
   `git log --remerge-diff` (git 2.36), a remote tip or a range cannot be
   determined, the push target is not a configured remote, or the scanner logs an
   error (an `ERR` line) although it exits 0. The variables `GIT_TRACE*` are
   removed from the scanner's environment, so a traced push is still scanned. The
   message names the
   cause and the recovery command, and prints no secret value and no remote URL. A
   range with no new commits passes with a line that says so.
4. A false positive is silenced only through gitleaks' own mechanisms: a
   `.gitleaksignore` fingerprint or a `gitleaks:allow` comment. Skipping the hook
   with `--no-verify` stays the Owner's action.
5. The scan makes no network call.

## Alternatives & Rationale

| Option | Verdict | Why |
|---|---|---|
| Keep scanning the working tree | Rejected | It cannot see a secret that a pushed commit adds and a later one removes. |
| Scan all reachable history on every push | Rejected | It rescans published history, which the policy excludes, and blocks on a secret that is already published. |
| Read the published tips with `git ls-remote` | Rejected | It puts a network call in the hook, which ADR-0072 point 2 excludes, and an unreachable remote would block every push. |
| For a new ref, exclude what the remote-tracking refs reach | Accepted | It needs no network. Its approximation is limit 1 below. |

## Consequences

Known limits. This section is the one place that records them.

1. Stale remote-tracking refs. A remote-tracking ref changes by fetch and push, so a
   commit reachable through it was fetched from or pushed to the remote once. A stale
   ref can therefore cause a re-publication of such a commit unscanned, not a first
   exposure. Mitigation: `git fetch --prune` before pushing a new branch.
2. A remote with no tracking ref (never fetched): the scan of a new ref covers the
   whole history of the branch.
3. Annotated tag messages are not scanned; gitleaks scans commit diffs.
4. `.gitleaks.toml` and `.gitleaksignore` are read from the pusher's working tree,
   not from the scanned commits.
5. git 2.36 or newer is required; an older git blocks the push.
6. The scan runs only where `scripts/install-hooks.sh` installed the hook.
7. The hook trusts the scanner's log: an `ERR` line blocks, which covers the failure
   measured here (git writes to stderr). An error that gitleaks swallows without an
   `ERR` line is not detected. A git warning on stderr blocks even a safe push until
   the cause is fixed.
8. The number of commits scanned is not checked. gitleaks 8.30.1 reports "0 commits
   scanned" for a delete-only, empty, mode-only, binary, rename-only or empty-file
   commit, so a check would block legitimate pushes; under trace it also reported a
   partial count (1 of 2), so it would not catch every silent case either.

`scripts/test-local-fs-path-rule.sh` and the `/verify` secret step keep their
`--no-git` working-tree scans on purpose: they check the rule and the current
tree, not a push.

## Confirmation & Revisit

Run at the hook as committed with this record, in a throwaway clone with fake
secrets and a local bare remote, by real `git push` (hook installed with
`git clone --template`) and by feeding git's pre-push input to the hook under
`/bin/bash` 3.2.57: add-then-remove, new branch with an early secret, a merge-only
secret, a force push, two refs in one push, a deletion, a missing scanner, a failing
scanner, a missing remote tip, and git without `--remerge-diff` (simulated by a
wrapper). Blocked cases exited 1 with no secret value in the output; safe cases
exited 0. Added for the trace defect, same method (real `git push`, hook at
`8a1e38e` against the hook of the fix): add-then-remove under `GIT_TRACE=1`,
`GIT_TRACE=2`, `GIT_TRACE2=1`, `GIT_TRACE_PERFORMANCE=1`, `GIT_TRACE2_EVENT=1`,
`GIT_TRACE2_PERF=1`, `GIT_TRACE_SETUP=1`, `GIT_TRACE_REFS=1`,
`GIT_TRACE=/dev/stderr` and three variables together, and under a git warning on
stderr; a secret under trace in a new branch and in an update; safe pushes under
trace; a push of delete-only, mode-only, binary, rename-only, empty-file and empty
commits ("0 commits scanned") that must pass. At `8a1e38e` 13 pushes with a secret
were published; with the fix none was. `GIT_TRACE=/dev/stdout` was not tested:
git itself fails the local push then. The harness is not committed (hook tests are deferred by the Owner), so
the run is not reproducible from this repository. The commit message states the
result.

Revisit if the Owner allows a network read in hooks (replace limit 1 by the remote's
current tips), or if the scanner is replaced.

## Source

The Owner's policy and the Owner's disposition of the stale-tracking-ref finding,
2026-11-19, executed in a Claude Code session with two independent review passes.
Claude Code drafted the text, so `source_type` is `inferred`. No external AI
cross-check was made.
