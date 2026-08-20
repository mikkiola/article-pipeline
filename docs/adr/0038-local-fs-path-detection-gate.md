# ADR-0038: Automated Detection Gate for Local Filesystem Path Leaks

Status: Accepted
Relates to: ADR-0018 (article-pipeline, personal path privacy in code)
— extends its territory without editing it, per Immutable Lineage
(ADR-0011): ADR-0018 decided the initial remediation (move existing
personal paths behind an environment variable or a gitignored config
file); this ADR adds an ongoing, automated detection gate against a
*new* path leaking in the future, which ADR-0018 never covered and its
own Validation section flagged as unverified ("Unverified as a discrete
technical check"). Also relates to `docs/BACKLOG.md`'s now-closed
"personal filesystem path" pilot-log entry (2026-08-21), whose fix this
ADR follows up on with a preventive mechanism.

## Context

A real instance of this class of leak was found and fixed: an immutable
pilot log's `skip_events[0].detail` field contained an absolute macOS
path (`/Users/<username>/Dev/gitlab.com/<username>/brain/...`), closed
via a superseding record rather than an in-place edit (Immutable
Lineage). Fixing the one instance doesn't prevent a new one from
entering a future commit — no automated check existed for this class of
leak at all.

The fix needed a distinction ADR-0018 never had to make, because it
only dealt with a small, known set of existing paths at decision time:
what to actually treat as sensitive. Local filesystem paths
(`/Users/<user>/...`, `/home/<user>/...`) reveal local machine
structure the owner doesn't want public. GitHub/GitLab usernames, repo
references, and profile URLs (e.g. `lyolich777ka`, `mikkiola`) are the
opposite — the owner's intentional, public portfolio identity, already
deliberately documented in `docs/ARCHITECTURE.md` and elsewhere, and
must keep showing up freely. A naive "personal identifier" scanner
would conflate the two; this decision does not.

## Decision

Extend the existing `.gitleaks.toml` (already this project's
established mechanism for exactly this kind of lightweight, custom
regex-based content check — the same file already carries a custom
`anthropic-api-key` rule fixing an earlier gitleaks false-negative) with
a new `local-fs-path` rule, rather than building a new script or
dependency. Runs at pre-push only, via the existing `gitleaks detect
--source . --no-git -v` call already in `scripts/hooks/pre-push` — no
new hook-wiring, no new tool.

1. **Pattern**: matches `/Users/<segment>/` and `/home/<segment>/`,
   anchored so a match must start a path-like token (line start, or
   preceded by whitespace/quote/paren) — not any occurrence of those
   substrings anywhere in a string. This anchoring is what keeps bare
   usernames and repo references (which never contain `/Users/` or
   `/home/` at all) structurally unable to match, without needing an
   explicit exception list of "safe" usernames.
2. **Allowlist, three exclusions, all verified empirically against this
   rule (not assumed)**:
   - A content-based exclusion (`regexTarget = "match"`, regex
     `://.*`) for a URL that happens to contain `/home/` as an ordinary
     path segment (e.g. `https://example.com/home/index.html`) —
     without it, a legitimate URL would false-positive.
   - A path-based exclusion for `claim_extraction/local_paths.json` and
     `evidence_package/output/_m4_staging*.json` — both `.gitignore`'d,
     never committed, but still visible to gitleaks' `--no-git` scan
     mode, which reads the raw filesystem rather than git's index and
     so doesn't respect `.gitignore`. Found via a dry run against the
     real repo before adoption, not assumed absent.
   - A path-based exclusion for this rule's own regression test script
     (`scripts/test-local-fs-path-rule.sh`), whose fixtures are
     deliberately shaped like real local paths for testing purposes and
     would otherwise flag the test script itself once committed.
3. **Placement is pre-push only, not pre-commit** — owner decision:
   push is the moment data actually leaves the machine and becomes
   public; a local commit carries no exposure risk yet. Matches this
   project's existing, established convention exactly (gitleaks and the
   ADR-citation check already live at pre-push, not pre-commit); adding
   gitleaks to pre-commit would be a separate, more disruptive change to
   that convention, unrelated to this decision.

## Options considered

| Option | Pros | Cons | Risks |
|---|---|---|---|
| A. Chosen: extend `.gitleaks.toml` with a scoped rule + allowlist, pre-push only | Reuses an already-integrated tool and an already-established pattern in this exact file (the Anthropic-key rule); zero new script, zero new hook-wiring; matches the existing pre-push-only placement of every other content-scanning check in this repo | gitleaks' `--no-git` mode doesn't respect `.gitignore`, requiring explicit path exclusions for known local-only files rather than that being automatic | A future gitignored file with a legitimate local path could false-positive until added to the allowlist — accepted as a narrow, low-cost gap, not solved generally here (would require changing gitleaks' scan mode project-wide, out of this decision's scope) |
| B. New standalone Python script (`scripts/check_local_paths.py`), invoked from a hook | Full control over matching logic (e.g. clean URL-exclusion via string checks instead of a content-regex allowlist) | New file, new hook-wiring, duplicates a tool (gitleaks) already doing exactly this class of check in this repo | Rejected: adds a second content-scanning mechanism alongside gitleaks for no capability gitleaks' allowlist mechanism doesn't already provide, once verified |
| C. Add gitleaks (with this rule) to pre-commit as well as pre-push | Catches a leak before it's even locally committed | Changes an established convention (gitleaks pre-push-only) as a side effect of an unrelated decision; commit is local-only, no exposure risk yet, so the marginal benefit is smaller than the convention-change cost | Rejected: owner's explicit reasoning — push is the actual exposure point, this decision shouldn't also relitigate hook placement |

## Chosen

A.

## Why

Option A reuses a tool this project already trusts and already extends
for exactly this class of problem, with zero new moving parts. Option B
would duplicate gitleaks' job with a new script for no functional gain
once the allowlist mechanism was verified to work. Option C conflates
two separate decisions — this rule's design, and gitleaks' hook
placement in general — the owner deliberately kept apart.

## Constraints

Does not change `docs/ARCHITECTURE.md`'s existing `lyolich777ka/brain.git`
reference or any other intentional public-identity reference — those
remain, unaffected, by design. Does not make gitleaks' `--no-git` scan
mode respect `.gitignore` generally — the three path exclusions are
scoped to this rule's allowlist only, not a project-wide fix. Does not
add gitleaks to pre-commit. Does not edit ADR-0018.

## Rejected

B — rejected as a needless duplicate of a tool already doing this job
once its allowlist mechanism was confirmed capable. C — rejected because
it conflates this rule's design with a separate, deliberately-unrelated
hook-placement decision.

## Consequences

- A future commit introducing a new local filesystem path will be
  caught at push time, not silently merged the way the original pilot
  log leak was.
- Any future gitignored file containing a legitimate local path (a
  fourth `local_paths.json`-style config, say) will need its own
  allowlist entry, same as the three added here — not automatic.
- `scripts/test-local-fs-path-rule.sh` is now a permanent regression
  test for this rule, not a one-off verification — re-run it after any
  future edit to `.gitleaks.toml`'s `local-fs-path` rule or allowlist.

## Validation

TDD per `docs/CONSTITUTION.md`'s TDD rule (a detection gate whose entire
job is triggering under specific conditions): `scripts/test-local-fs-path-rule.sh`
written first, confirmed RED against the pre-rule `.gitleaks.toml`
(failed for the right reason — the rule didn't exist yet), then GREEN
after adding the rule. Two real implementation bugs were caught and
fixed during this process, not just the RED/GREEN cycle itself: an
initial rule-level `path` field using negative-lookahead crashed
gitleaks outright (its RE2 engine doesn't support lookahead — fixed by
using the allowlist's `paths` list instead), and the test's own
real-repo sanity check initially used an absolute `--source` path,
which reports absolute finding paths that don't match the allowlist's
relative-path regexes — a false test failure, not a real one — fixed by
invoking gitleaks the same way the production hook actually does
(relative `.` source, cwd = repo root).

## Reversal condition

If gitleaks' `--no-git`/`.gitignore` mismatch causes repeated false
positives on gitignored local files beyond what a per-rule allowlist
can reasonably keep up with, revisit this ADR — likely toward changing
gitleaks' invocation to respect `.gitignore` project-wide, which is out
of this ADR's scope as written.

## Source

Article-pipeline session, 2026-08-21, following the pilot-log path
redaction. Design and allowlist entries verified empirically via
`scripts/test-local-fs-path-rule.sh` and direct dry runs against the
real repo before adoption, not assumed correct from gitleaks'
documentation alone.
