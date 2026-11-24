---
id: ADR-0077
status: Accepted
supersedes: null
superseded_by: null
source_type: inferred
---

# ADR-0077: The pre-push secret scan covers the commits a push publishes

## Status

Accepted. Dates and commits: `git log --format='%h %ad' --date=short -- <this file>`.

- 2026-11-19, decision: the Owner's policy and limits 1 to 8 (34bd00a); corrected the same day in
  0424865.
- 2026-11-20, correction: 3654091 (points 2 to 4; limits 9 to 12 record audit findings and one
  fix cost, not decisions).
- 2026-11-20, decision: the Owner chose option C: block a push that publishes a commit with
  three or more parents, and accept UTF-16 files as a known limit (limit 13). Implemented in
  8b4e608 (2026-11-24).
- 2026-11-24, correction: the commit that carries this text withdraws the recovery of point 6
  and corrects limits 1 and 9 to 11, Confirmation and Source.

The dates of the Owner's decisions are those stated in 34bd00a ("Accepted on 2026-11-19") and in
the message of 8b4e608; `git log` does not show them. The Decision was edited in place at the
Owner's instruction. The record is not on `main`: `git log origin/main -- <this file>` printed
nothing on 2026-11-24.

The supersession is partial (DR-6) and names one point of ADR-0038: the scan that its Decision
names, "the existing `gitleaks detect --source . --no-git -v` call already in
`scripts/hooks/pre-push`", and the statements that follow from that scan mode (that it reads the
raw filesystem and does not respect `.gitignore`). In force, unchanged: ADR-0038's
`local-fs-path` rule, its allowlist in `.gitleaks.toml`, and the placement at pre-push. The
frontmatter fields stay null (ADR-0076); ADR-0038 is not edited.

## Context & Constraints

Observations 1 to 4 come from earlier sessions and audits whose scripts are deleted; Confirmation
repeats them only where it says so.

1. At `d365906`: `git show d365906:scripts/hooks/pre-push | sed -n 39,48p` prints
   `gitleaks detect --source . --no-git -v --redact`, which reads the files on disk. A secret
   that one pushed commit adds and a later one removes is not on disk, so the push publishes it
   unscanned (a throwaway clone, a fake secret: exit 0, "no leaks found").
2. At `8a1e38e`, by real `git push`: with `GIT_TRACE=1` the same push exited 0 and published the
   secret. gitleaks ends its scan on the first byte its own `git log` writes to stderr, logs
   `ERR error="stderr is not empty"` and exits 0 with "0 commits scanned"; a git warning does the
   same.
3. Audit (Codex, 2026-11-19) of `0424865`, by real `git push`: a secret was published with hook
   exit 0 when `GITLEAKS_CONFIG` or `GITLEAKS_CONFIG_TOML` replaced the repository's
   configuration; when git printed no diff for the file (a `-diff` or `binary` attribute, a
   textconv driver, a NUL byte); and when the command that searched the scanner log for an `ERR`
   line failed, read as "no error".
4. Audit (Codex, 2026-11-20) of `3654091`: a secret added by a three-parent commit was published
   with hook exit 0, because `git log --remerge-diff` prints no added text for it (repeated,
   Confirmation 1); so was a secret in a UTF-16LE file (repeated, Confirmation 2).

Constraints: the hook makes no network call (ADR-0072, point 2). The scanner redacts the value of
a finding, not the commit Author name (limit 11). The scanner stays gitleaks (`gitleaks version`
prints 8.30.1 on the test machine). Threat model: the hook protects against accidental leaks in
normal work, not against a pusher who controls the environment, the git configuration or
`.gitattributes` on purpose, or who skips it with `--no-verify` (the Owner's action).

## Decision

The pre-push hook scans, with gitleaks, the commits that the push makes reachable on the remote,
ref by ref. The working tree is not scanned and is not evidence.

1. Range. An updated ref, including a force push: the commits from the remote tip that git
   passes to the hook up to the pushed tip. A new ref: the commits of the pushed tip that no
   remote-tracking ref of that remote reaches. A deleted ref: nothing to scan. A commit with two
   parents is scanned for what the merge itself adds. A commit with three or more parents (an
   octopus merge) is not scanned, because git shows none of what it adds: the push that
   publishes one is blocked (point 6).
2. Commits that the remote tip of the pushed ref (an update) or a remote-tracking ref (a new
   ref) reaches are not rescanned. A commit that only another branch published is rescanned for
   an updated ref (limit 9).
3. The hook blocks the push when the scanner finds a secret, and when it detects that the scan
   did not complete: the scanner is missing or fails, git fails or lacks
   `git log --remerge-diff` (git 2.36), a remote tip or a range cannot be determined, the push
   target is not a configured remote, the scanner logs an error (an `ERR` line) although it
   exits 0, or the search for that line returns any status but "no match" (bash's own matcher
   does it, so no external command can fail into "no error"). `GIT_TRACE*` and `GITLEAKS_*`
   variables are removed from the scanner's environment, so the repository's `.gitleaks.toml`
   decides. git prints every file as text (`--text --no-textconv`), so an attribute, a NUL byte
   or a textconv driver does not hide bytes. Except in point 6, the message names the cause and a
   recovery, and prints no remote URL. A range with no new commits passes with a line that says
   so.
4. A false positive is silenced only through gitleaks' own mechanisms. A `.gitleaksignore`
   fingerprint and an allowlist in `.gitleaks.toml` are read from the pusher's working tree
   (limit 4). A `gitleaks:allow` comment is read from the scanned commit's own diff: it counts
   only when committed, on the line of the finding.
5. The scan makes no network call.
6. A push that publishes a commit with three or more parents is blocked, also when the commit
   adds no secret. A commit counts as published when it is in the range of point 1 for that ref:
   a merge that another ref already published blocks an updated ref (limit 9). If git cannot
   report the parent count, the push is blocked. The message names the cause and the commit,
   prints no secret value, points to this point and prints no recovery command. Recovery is
   manual. Known hazards: (a) a merge rebuilt from fewer parents than it has loses the work of
   the others, and the replacement push passes; (b) steps that go on after a failed one
   (`git switch -c` onto an existing branch, then merges) merge on the checked-out branch; (c)
   `git rebase <remote>/<branch>` drops the changes that only the merge made, or, with
   `rebase.rebaseMerges=true`, keeps the octopus merge and the push stays blocked.

## Alternatives & Rationale

| Option | Verdict | Why |
|---|---|---|
| Keep scanning the working tree | Rejected | It cannot see a secret that a pushed commit adds and a later one removes. |
| Scan all reachable history on every push | Rejected | It rescans published history, which the policy excludes, and blocks on a secret that is already published. |
| Read the published tips with `git ls-remote` | Rejected | It puts a network call in the hook, which ADR-0072 point 2 excludes, and an unreachable remote would block every push. |
| For a new ref, exclude what the remote-tracking refs reach | Accepted | It needs no network. Its approximation is limit 1 below. |
| Print a recovery in the block message | Rejected | The printed recovery had three reproduced defects (point 6, a to c). |

## Consequences

Known limits:

1. A stale remote-tracking ref can cause a commit that the remote once held to be re-published
   unscanned and past the octopus block, not first exposed. Mitigation: `git fetch --prune`.
2. A remote with no tracking ref (never fetched): a new ref is scanned over the whole history of
   the branch.
3. Annotated tag messages are not scanned.
4. `.gitleaks.toml` and `.gitleaksignore` are read from the pusher's working tree, not from the
   scanned commits.
5. git 2.36 or newer is required; an older git blocks the push.
6. The scan runs only in a clone where the hook is installed. `scripts/install-hooks.sh`
   copies the tracked file, so an installed copy stays as it was until the script runs again.
7. The hook trusts the scanner's log: an error that gitleaks swallows without an `ERR` line is
   not detected. A git warning on stderr blocks even a safe push.
8. The number of commits scanned is not checked: gitleaks 8.30.1 reports 0 for a commit that
   adds no text, so a check would block legitimate pushes.
9. An updated ref is scanned from its own remote tip: a commit published through another branch
   is scanned again and can block, an octopus merge included, also without a secret. This is an
   accepted Owner policy cost.
10. Binary files are scanned as text. A large binary file can make the scan slow; the cost is
    not measured in this record.
11. `--redact` hides the secret value of a finding, not the commit metadata that gitleaks prints
    with it: with a finding in the push, an Author name that holds a key is printed as it is.
12. Some failures print a prose recovery. The printed gitleaks command uses the caller's
    environment, not the hook's cleaned one.
13. UTF-16 files: a secret inside a UTF-16-encoded file is not detected, because `--text` prints
    the bytes but does not decode them, and NUL bytes separate the characters of the key. A
    decoding step is not part of this decision.

## Confirmation & Revisit

Run on 2026-11-24 (git 2.44.0, gitleaks 8.30.1, `/bin/bash` 3.2.57) against the tracked
`scripts/hooks/pre-push` of the commit that carries this text. Real `git push` to a local bare
remote; fake secrets generated at run time, never printed. The scripts are outside the repository
(hook tests are deferred by the Owner); the commit message gives their sha256 and the hook's.

1. `python3 -I scenarios.py scripts/hooks/pre-push .`: 12 of 12 checks pass (octopus block,
   two-parent merge scan, ordinary pushes, unreadable parent count). Against the hook of
   `3654091`: 5 FAIL, 7 PASS. They are not five vulnerabilities: one is the gap (a three-parent
   merge with a secret is pushed), three are the missing block, parent-count failure and message,
   one is the recovery push, rejected as non-fast-forward because the first push had published
   the merge.
2. `python3 -I repro.py scripts/hooks/pre-push . norecipe`: all checks pass: the message of
   point 6, hazards a to c, limits 1 and 9, limit 11, limit 13 (UTF-16LE and UTF-16BE; a UTF-8
   control blocks). Mode `recipe` against the hook of `8b4e608` reproduces the three defects of
   the recovery it printed.
3. Stubs: in 1 and 2 the pin check, the DocOps check and the two shell checks
   (`scripts/tt_pin_check.py`, `scripts/docops.py`, `scripts/check-adr-citation.sh`,
   `scripts/check-doc-pairing.sh`) are stubs that exit 0. These runs show the secret-scan and
   octopus paths of the hook only.
4. Unstubbed: a scratch clone with the real pin check and DocOps check, the materialized files
   equal to the real checkout's by sha256, the hook installed by `scripts/install-hooks.sh`. A
   clean push exits 0, a push with a fake secret exits 1, a push of a three-parent merge exits 1.
   `scripts/check-doc-pairing.sh` skipped its comparison ("No upstream branch").
5. Not reproduced, not claimed: the scripts for `0424865` and `3654091` are deleted; their counts
   (92 scenarios, 2 of 2, 5 of 5, 1 of 1) and the timing of a 30 MB binary file are unverified
   history. Not run on 2026-11-24, so not verified here: a git older than 2.36; the failure
   paths of point 3 other than the parent count; the allowlist sources of point 4; limits 2 to 8
   and 12 (carried from earlier accepted text).

Revisit if the Owner allows a network read in hooks (replace limit 1 by the remote's current
tips), or if the scanner is replaced.

## Source

The Owner's policy and disposition of the stale-tracking-ref finding, 2026-11-19, and the
decision of 2026-11-20 (option C), executed in Claude Code sessions. The Codex audits and the
independent read of `8b4e608` (Hansard library item lib_724753d40ef1b046: recovery defects, the
range of one ref, the Author name) are external AI input; the findings that this text relies on
were reproduced before it changed (Confirmation 1 and 2). Claude Code drafted the text, so
`source_type` is `inferred`.
