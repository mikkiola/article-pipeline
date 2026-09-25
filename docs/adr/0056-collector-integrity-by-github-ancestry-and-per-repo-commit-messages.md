---
id: ADR-0056
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0056: Collector records are verified by GitHub ancestry, and commit messages are attributed per repository

## Status

Accepted.

## Context & Constraints

The bootstrap gate's integrity check (`strategy_layer/adapters/collector.py`) did not
provide the guarantee it was designed for. Direct investigation of the code, the CI
logs of workflow runs 35995489345 (2026-09-24) and 36082913065 (2026-09-25), and the
history of `SPEC.md` found two independent causes.

**Cause 1 — the check compared against the wrong data.** `check_integrity()` compared
the commit count a Collector brief reported against `git rev-list --count` on the
*current HEAD of a local checkout*, over a window anchored at 23:59:59 UTC of the
brief's date. Two things were wrong, and either alone would have been enough:

- The publish workflow checks out only `article-pipeline`, `collector` and
  `registry-data`, each at `fetch-depth: 1`. The other repositories a brief names
  (`archi-kg`, `brain`, `radar`, `radar-vault`, `tooltempest`) were never present, so
  their units were always `invalid`. For the two that were present, a depth-1 clone
  holds exactly one commit, so the reconciled count was 0 or 1 regardless of what
  happened that day. On 2026-09-24 `collector` verified only because its reported
  count (1) happened to equal the tip commit of the shallow clone; `article-pipeline`
  (reported 13, reconciled 1) failed. On 2026-09-25 every unit was invalid and the
  gate blocked.
- Even with full history, "the count on HEAD now" is not "what Collector saw when it
  scanned". Collector scans relative to whenever it runs; a later HEAD, a rewritten
  history or a different window all move the number. The check was structurally
  unable to answer the question it was named for.

**Cause 2 — commit messages bypassed the gate.** `commit_messages` in Collector's
daily brief was a flat, cross-repository list of subject strings with no per-message
attribution. The adapter attached the same full list to every unit it built, and
`AuthoringContext`/`linkedin_verdict_reader` copied an included unit's list into the
post prompt. A rebuilt 2026-09-24 prompt listed one repository in `per_repo` and
`total commits: 1`, yet carried 19 subjects from four repositories, including
repositories the gate had excluded. The include/exclude decision governed `per_repo`,
`total_diffstat` and `files_touched`, but not the message text — the one field most
likely to shape the post.

**A process cause behind both.** The check was specified in an earlier `SPEC.md`
("`git rev-list --count` for the reported window roughly matches the reported
`commit_count`", tolerated "beyond tolerance"). That text no longer exists in
`SPEC.md`: the Living Spec was overwritten wholesale by the Publication Core Loop
specification, and the implementation had silently become an exact match with an
ad-hoc anchor. Nothing checked that the enforced semantics of the overwritten section
had been carried into the new text or an ADR. This is recorded as a separate backlog
item and is not designed here.

Constraints: one trust boundary — the owner controls Collector and the publisher under
the same GitHub App; no new credential; the workflow's checkout list stays as it is;
`publication_registry/`, `linkedin_client.py`, SAFETY_PAUSE and the token preflight are
untouched.

## Decision

1. **Collector records the branch tip it observed.** `tier0_scan.py` adds `head_sha`
   (`git rev-parse HEAD`) to every scanned repository, *including repositories with zero
   commits in the window* — per-commit SHAs do not exist when `commit_count` is 0, so a
   tip cannot be derived from them. The weekly manifest carries `head_sha`; the daily
   brief (now `schema_version: 2`) carries `branch` and `head_sha` per repo. The field is
   named `head_sha` everywhere.

2. **Integrity is ancestry, checked through the GitHub REST API.**
   `check_integrity(repo_name, branch, head_sha)` calls
   `GET /repos/{owner}/{repo}/compare/{head_sha}...{branch}` and is `valid` iff the
   response has `behind_by == 0` (status `identical`, or `ahead` when the branch has moved
   on since the scan). It is `invalid` for `behind`, `diverged` (the SHA is on some other
   branch), 404 (SHA, repo or branch does not exist), any other HTTP status, any request
   failure, a missing token, or a record with no `head_sha`/`branch`. There is no fallback
   to a local checkout and no tolerance: exact comparison against the SHA Collector
   observed. `INTEGRITY_CHECK_METHOD` is renamed `ancestry_reconciliation`. The
   directory name `radar-vault` maps to repository `radar` for the API call only.

3. **One shared path.** `adapt_manifest()` and `adapt_daily_brief()` both call the same
   `check_integrity()`. A manifest or brief written before `head_sha` existed, or a brief
   whose `schema_version` is not 2, fails closed: its units are `invalid` and no API call
   is made.

4. **Commit messages are attributed per repository.** Collector's `commit_messages`
   becomes a list of `{repo, sha, subject}` objects. The adapter gives each unit only the
   subjects whose `repo` is that unit's repository. Because `AuthoringContext` is built
   only for `final_classification == "include"` units and the verdict reader merges only
   those contexts' own slices, a message from an excluded or invalid unit has no path
   into `daily_linkedin_author.build_prompt()`. A malformed message entry raises rather
   than being guessed into some repository's slice.

5. **No cryptographic signing or attestation** (Sigstore, SLSA provenance, OIDC-based
   signing) of the daily brief, and no "future hardening" stub for it. This pipeline has
   one trust boundary: the owner controls both Collector and the publisher under the same
   GitHub App credential. Signing defends against a party who can tamper with the brief
   but is not already able to act as the publisher; no such party exists here. Adding it
   would add machinery and key management without changing who can publish.

6. **Credential plumbing.** The publish job's App token now lists `article-pipeline`,
   `collector`, `tooltempest`, `radar`, `archi-kg` and `brain` (the list Collector's own
   daily workflow already uses) and reaches the publish step as `GITHUB_APP_TOKEN`. It is
   deliberately not named `GH_TOKEN`/`GITHUB_TOKEN`: the `gh` CLI reads those, and setting
   them would switch on `daily_linkedin_author`'s public-repo link lookup as a side
   effect.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Keep count reconciliation; make CI check out all repos with `fetch-depth: 0`. | Rejected. Fixes the shallow clone but not Cause 1's second half: a count on today's HEAD still is not the state Collector observed. It also enlarges the checkout list, which is out of scope, and needs the same seven full clones the Collector job already makes. |
| B. Check ancestry against a local clone. | Rejected. Needs full history and every repository checked out; the API answers the same question with no checkout. |
| C. Chosen — record the observed tip in Collector; verify ancestry via the GitHub compare API. | Compares against the right data, works for repositories that are not checked out, works for zero-commit repositories, and removes the shallow-clone problem for the two that are. |
| D. Sign the brief (Sigstore / SLSA / OIDC). | Rejected explicitly (Decision 5): one trust boundary, no adversary the signature would stop. |
| E. Keep the flat message list and filter it in the prompt builder. | Rejected. Without attribution the builder cannot know which message belongs to which repository; any filter would be a guess. Attribution has to originate where the SHA and repository are known — Collector's scan. |
| F. Leave `adapt_manifest()` on the old local check. | Rejected by the owner (2026-09-25): the same structural flaw would remain for the weekly path; both paths now share one check. |

## Consequences

- **Known limitation — zero-commit repositories.** A repository with no commits in the
  window gets a real `head_sha` and verifies as "this repository, branch and SHA are
  real". Ancestry cannot and does not confirm that *zero commits actually happened* in the
  window; it is not stronger than that for them.
- **Known limitation — what ancestry proves.** It proves the recorded SHA exists in the
  branch's history. It does not verify `commit_count`, `diffstat`, `files_touched`, or the
  individual per-message SHAs, and a SHA far back in history passes just as a fresh one
  does. The earlier count check verified a number (wrongly); this one verifies a
  relationship (correctly, but a narrower claim). `commit_messages[].sha` is recorded so a
  later check can verify each message, but none does today.
- **Old data fails closed.** Every existing `daily_brief_*.json` and `manifest_*.json`
  (all written before `head_sha`) produces only `invalid` units. Only briefs and
  manifests generated after Collector's change verify.
- **Unverified until the first scheduled run.** That article-pipeline's `GH_APP_ID` /
  `GH_APP_PRIVATE_KEY` are the same App as Collector's, and that the installation grants
  read access to `tooltempest`, `radar`, `archi-kg` and `brain`, could not be confirmed
  without triggering the publishing workflow (which publishes to LinkedIn). Collector's
  own workflow requests the same six repositories and succeeds, which is the evidence for
  it. If the token lacks access to a repository, its units are `invalid` (HTTP 403/404) —
  fail closed, with no fallback to a local checkout for some repositories and the API for
  others.
- **Now more likely to publish.** With correct verification, more units pass, so the
  bootstrap gate will block less often, and a post can draw on several repositories'
  data — each with only its own commit messages. This is the intended effect, and it means
  the first scheduled run after deployment may publish for real.
- `linkedin_publisher/daily_publish.py` prints only `units built: N` and the gate result;
  per-unit `integrity_check_detail` is not printed anywhere in the logs. Confirming which
  repositories verified in a real run needs that detail surfaced (not done here: outside
  this decision's scope).
- `daily_linkedin_author._build_fact_prompt` still tells the model commit messages "are
  not attributed to a repository". That is now conservative rather than true; it was left
  unchanged because changing the prompt is a separate content decision.
- `INTEGRITY_CHECK_METHOD` changes from `commit_count_reconciliation` to
  `ancestry_reconciliation`, so the `reason` text `pre_filter` writes for an invalid unit
  names the new method. ADR-0047's two-dimension model is unchanged; only the mechanism it
  named for Collector's `integrity_status` is amended here. `strategy_layer/adapters/
  collector.py` no longer runs any `git` command or reads the local filesystem.
- Deployment order matters once: an article-pipeline adapter that meets an old-shape brief
  blocks (fail closed) rather than crashing, so the two repositories may be pushed in
  either order.

## Confirmation & Revisit

Confirmed by construction: `strategy_layer/adapters/test_collector.py` (mocked GitHub
responses for identical / ahead / behind / diverged / 404, other HTTP errors, request
exceptions, missing token, missing `head_sha`/`branch`, the `radar-vault` mapping, per-repo
slices, unknown `schema_version`), and `author/test_no_message_bypass.py` (a 7-unit brief
with one included unit: only that unit's messages reach the built prompt). A live smoke
run on 2026-09-25 (real local scan → real GitHub API, using the owner's own token rather
than the App token) verified pushed tips as valid, mapped `radar-vault` to `radar@vault`,
rejected unpushed local tips with 404, and failed closed on a real pre-`head_sha`
manifest.

Not yet confirmed: a scheduled workflow run with the App token (see Consequences).
Revisit when Brain gets its own adapter (ancestry may not be the right integrity notion
for a source that is not a git repository), when the App's repository access changes, or
if a check of `commit_messages[].sha` / `commit_count` is wanted — that would be a new ADR
extending this one, not an edit to it.

## Source

Owner task, 2026-09-25, following a read-only investigation of workflow runs
35995489345 and 36082913065, the Strategy Layer/Author code path and `SPEC.md` history,
and the owner's answer on how the weekly-manifest path should be handled.
