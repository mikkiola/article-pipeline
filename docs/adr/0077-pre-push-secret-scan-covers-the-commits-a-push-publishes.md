---
id: ADR-0077
status: Accepted
supersedes: null
superseded_by: null
source_type: inferred
---

# ADR-0077: The pre-push secret scan covers the commits a push publishes

## Status

Accepted on 2026-11-19. The policy and limits 1 to 8 are the Owner's decisions.
Limits 9 to 12 record Codex audit findings (Context) and one fix cost; they are
not decisions. On 2026-11-20 the Owner decided (option C) to block a push that
publishes a commit with three or more parents and to accept UTF-16 files as a
known limit (limit 13). The Decision and the limits were corrected on 2026-11-19, before
this record reached `main`, at the Owner's instruction. The supersession is partial (DR-6) and names one point of ADR-0038:
the scan that its Decision names, "the existing `gitleaks detect --source . --no-git -v`
call already in `scripts/hooks/pre-push`", and the statements that follow from
that scan mode (that it reads the raw filesystem and does not respect
`.gitignore`). In force, unchanged: ADR-0038's `local-fs-path` rule, its
allowlist in `.gitleaks.toml`, and the placement at pre-push. The frontmatter
fields stay null (ADR-0076); ADR-0038 is not edited.

## Context & Constraints

Observation at `d365906`: `git show d365906:scripts/hooks/pre-push | sed -n 39,48p`
prints `gitleaks detect --source . --no-git -v --redact`, which reads the files on
disk. A secret that one pushed commit adds and a later one removes is not on disk,
so the push publishes it unscanned. In a throwaway clone with a fake secret, that push
exited 0 with "no leaks found".

Second observation, at `8a1e38e`, by real `git push`: with `GIT_TRACE=1` the same
push exited 0 and published the secret. gitleaks ends its scan on the first byte
its own `git log` writes to stderr, logs `ERR error="stderr is not empty"` and
exits 0 with "0 commits scanned"; a git warning does the same.

Third observation, an independent audit (Codex, 2026-11-19) of `0424865`, each
finding reproduced by real `git push` (Confirmation). A push published a secret with
hook exit 0 when `GITLEAKS_CONFIG` or `GITLEAKS_CONFIG_TOML` replaced the repository's
configuration; when git printed no diff for the file (a `-diff` or `binary`
attribute, a textconv driver, a NUL byte); and when the command that searched the
scanner log for an `ERR` line failed, read as "no error".

Fourth observation, an independent read-only audit (Codex, 2026-11-20) of
`3654091`, by real `git push` (Confirmation): a secret added by a commit with
three parents was published with hook exit 0 (2 of 2), because
`git log --remerge-diff` prints no added text for it; a secret in a UTF-16LE file
was published with hook exit 0 (3 of 3). Both existed at `0424865`.

Constraints: the hook makes no network call (ADR-0072, point 2). The scanner
redacts the value of a finding, not the commit author metadata (limit 11). The scanner stays gitleaks (`gitleaks version` prints
8.30.1 on the test machine). Threat model: the hook protects
against accidental leaks in normal work, not against a pusher who controls the
environment, the git configuration or `.gitattributes` on purpose, or who skips it
with `--no-verify` (the Owner's action).

## Decision

The pre-push hook scans, with gitleaks, the commits that the push makes reachable
on the remote, ref by ref. The working tree is not scanned and is not evidence.

1. Range. An updated ref, including a force push: the commits from the remote tip
   that git passes to the hook up to the pushed tip. A new ref: the commits of the
   pushed tip that no remote-tracking ref of that remote reaches. A deleted ref:
   nothing to scan. A commit with two parents is scanned for what the merge itself adds. A commit with
   three or more parents (an octopus merge) is not scanned, because git shows none
   of what it adds: the push that publishes one is blocked (point 6).
2. Commits that the remote tip of the pushed ref (an update) or a remote-tracking
   ref (a new ref) reaches are not rescanned. A commit that only another branch
   published is rescanned for an updated ref (limit 9).
3. The hook blocks the push when the scanner finds a secret, and when it detects
   that the scan did not complete: the scanner is missing or fails, git fails or
   lacks `git log --remerge-diff` (git 2.36), a remote tip or a range cannot be
   determined, the push target is not a configured remote, the scanner logs an
   error (an `ERR` line) although it exits 0, or the search for that line returns
   any status but "no match" (bash's own matcher does it, so no external command
   can fail into "no error"). `GIT_TRACE*` and `GITLEAKS_*` variables are removed
   from the scanner's environment, so the repository's `.gitleaks.toml` decides.
   git prints every file as text (`--text --no-textconv`), so an attribute, a NUL
   byte or a textconv driver does not hide bytes. The message names the cause and
   a recovery, and prints no remote URL. A range with no new commits passes with a
   line that says so.
4. A false positive is silenced only through gitleaks' own mechanisms. A
   `.gitleaksignore` fingerprint and an allowlist in `.gitleaks.toml` are read
   from the pusher's working tree (limit 4). A `gitleaks:allow` comment is read
   from the scanned commit's own diff: it counts only when committed, on the line
   of the finding.
5. The scan makes no network call.
6. A push that publishes a commit with three or more parents is blocked, also when
   the commit adds no secret. A commit counts as published when it is in the range
   of point 1. If git cannot report the parent count, the push is blocked. The
   message names the cause, prints no secret value and gives a recovery that
   rewrites the merge as ordinary two-parent merges or a rebase.

## Alternatives & Rationale

| Option | Verdict | Why |
|---|---|---|
| Keep scanning the working tree | Rejected | It cannot see a secret that a pushed commit adds and a later one removes. |
| Scan all reachable history on every push | Rejected | It rescans published history, which the policy excludes, and blocks on a secret that is already published. |
| Read the published tips with `git ls-remote` | Rejected | It puts a network call in the hook, which ADR-0072 point 2 excludes, and an unreachable remote would block every push. |
| For a new ref, exclude what the remote-tracking refs reach | Accepted | It needs no network. Its approximation is limit 1 below. |

## Consequences

Known limits:

1. A stale remote-tracking ref can cause a commit that the remote once held to be
   re-published unscanned, not first exposed. Mitigation: `git fetch --prune`.
2. A remote with no tracking ref (never fetched): a new ref is scanned over the
   whole history of the branch.
3. Annotated tag messages are not scanned.
4. `.gitleaks.toml` and `.gitleaksignore` are read from the pusher's working tree,
   not from the scanned commits.
5. git 2.36 or newer is required; an older git blocks the push.
6. The scan runs only in a clone where the hook is installed. `scripts/install-hooks.sh`
   copies the tracked file, so an installed copy stays as it was until the script
   runs again.
7. The hook trusts the scanner's log: an error that gitleaks swallows without an
   `ERR` line is not detected. A git warning on stderr blocks even a safe push.
8. The number of commits scanned is not checked: gitleaks 8.30.1 reports 0 for a
   commit that adds no text, so a check would block legitimate pushes.
9. An updated ref is scanned from its own remote tip: a commit published through
   another branch is scanned again and can block.
10. Binary files are scanned as text: `/usr/bin/time -l gitleaks detect` on a 30 MB
    random binary took 147 s, against 0.25 s without `--text`.
11. `--redact` hides the secret value in the scanner output, not the commit
    Author name, email and date of a finding: with a finding in the push, an Author
    name that holds a key prints it unredacted (Codex reproduction, 2026-11-20).
12. Some failures print a prose recovery. The printed gitleaks command uses the
    caller's environment, not the hook's cleaned one.
13. UTF-16 files: a secret inside a UTF-16-encoded file is not detected, because
    `--text` prints the bytes but does not decode them, and NUL bytes separate the
    characters of the key. A decoding step is not part of this decision.

## Confirmation & Revisit

Method: a throwaway clone, fake secrets made at run time, a local bare remote, real
`git push` (`git clone --template` hook), `/bin/bash` 3.2.57. 92
scenarios ran twice: against `git show 0424865:scripts/hooks/pre-push`, then against
the hook file of this commit. Before, then after: `GITLEAKS_CONFIG` or
`GITLEAKS_CONFIG_TOML` set, 2 of 2 pushes with a secret published, then 0; a `-diff`
or `binary` attribute, a textconv driver, a NUL byte or an injected
`core.attributesFile`, 5 of 5, then 0; a `grep` that exits 2 for the `ERR` search,
1 of 1, then 0 (a hook copy whose match returns status 2 blocked). All other
scenarios, among them pushes that gitleaks counts as "0 commits scanned", gave the
same result, except `GITLEAKS_CONFIG=/nonexistent`, which no longer fails the
scanner. The harness is not committed (hook tests are
deferred by the Owner), so the run is not reproducible from this repository; the
commit message states the result.

Octopus block (point 6), added 2026-11-20: real `git push` to a local bare remote
with fake secrets, the tracked hook of the commit that adds the block. A
three-parent merge with and without a secret is blocked; an octopus commit already
on the remote does not block a later push; ordinary and two-parent pushes behave as
before; an unreadable parent count blocks with its cause. Command:
`python3 -I scenarios.py scripts/hooks/pre-push .` (script outside the repository,
named in the commit message), `/bin/bash` 3.2.57, git 2.44.0, gitleaks 8.30.1: 12
checks PASS. The same script against the hook of `3654091`: the 5 octopus and
parent-count checks FAIL (the gap), the 7 others PASS. Limits 11 and 13 rest on
the Codex audit above, not on this run.

Revisit if the Owner allows a network read in hooks (replace limit 1 by the remote's
current tips), or if the scanner is replaced.

## Source

The Owner's policy and disposition of the stale-tracking-ref finding, 2026-11-19,
executed in Claude Code sessions. The audit of `0424865`
(Codex) is external AI input: its HIGH findings were reproduced before the fix.
Claude Code drafted the text, so `source_type` is `inferred`.
