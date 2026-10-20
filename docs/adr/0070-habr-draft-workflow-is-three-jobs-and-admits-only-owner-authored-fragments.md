---
id: ADR-0070
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0070: The Habr draft workflow is three jobs, and a fragment is admitted only when its commit's author is an owner identity

## Status

Accepted on 2026-10-15 as a decision. Not yet confirmed by a real run. It
refines points 1 and 2 of ADR-0069 and does not reverse any of them. Point 3
and its context were revised on 2026-10-16, before this ADR was first
committed, by the owner's decision after an investigation of the repositories'
access model: the five-category identity classification, the AI and bot
policies and the per-commit waiver were replaced by an author check. Points 1
and 2 are unchanged.

## Context & Constraints

ADR-0069 separated a broad-token stage from the paid stage but placed both in
one workflow job. Reading the runtime workflow's run log (job log of run
38667071401, 2026-10-15) showed what that leaves open:

- `actions/checkout@v4` defaults to `persist-credentials: true`; each checkout
  writes its token to `.git/config` as `http.https://github.com/.extraheader`
  and removes it only in the job's post step. A broad token used to check out
  the private Collector therefore stays on disk, in the same job and the same
  user, while the paid stage runs. Scoping a token to a step's `env` does not
  prevent that.
- A registry-data checkout in the same job leaves the write credential on disk
  during the paid stage as well.
- Commit metadata (author, committer, `Co-authored-by` trailers) establishes
  which identity wrote a commit only as far as the repository's push access
  does; it is not authentication. Access, read from the GitHub API and the
  local clones on 2026-10-16: `article-pipeline`, `radar` and `tooltempest`
  belong to the personal account `mikkiola`; each lists exactly one
  collaborator, `mikkiola`, and has no pending invitation, deploy key, webhook
  or fork; no workflow pushes to `main`. The only pull requests ever opened are
  one in `article-pipeline` and one in `tooltempest`, both by the owner;
  `radar` has none. Every push to `main` in the retained event window (from
  2026-09-15 to 2026-09-30, depending on the repository) came from `mikkiola`,
  the account Claude Code works under. Not established: who pushed older
  commits, and the write permissions of the GitHub App installation (its
  installations cannot be listed with the owner's token); the App's key
  belongs to the owner, the same trust boundary as ADR-0056 point 5.
- What `main` contains: all 38 commits of the three allow-listed repositories
  that appear in the Collector's daily briefs (2026-09-03 to 2026-10-01) are
  authored by the owner. Of the 305 `Co-authored-by` trailers on the three
  `main` branches (233, 56 and 16), every one is `noreply@anthropic.com`; no
  commit has an AI author and none has a human co-author. Other authors:
  `Radar Bot <radar@gitlab.com>` (no GitHub login; 13 commits in `radar`, 18 in
  `tooltempest`; a git-config identity, not the Actions identity
  `radar@github.com`, which writes only to the `vault` branch) and the owner's
  second account `OStroganova` (73 commits in `radar`, written under a
  work-domain address, the last on 2026-06-26).
- The owner is the author of every article this system produces. Who wrote a
  fragment or created a commit does not decide that. The question the
  admission rule serves is narrower: not putting a third party's code into a
  public article without a basis. `SPEC.md` and the ADRs contain no requirement
  to disclose AI involvement in a code fragment.

## Decision

1. **Three jobs; each runtime credential exists in one job, except the App
   private key (see Consequences).**
   - `prepare`: broad GitHub App token; reads the daily brief and the private
     Collector; no model call; no registry-data. Its only output is the
     validated, scrubbed `selection_input.json`, passed as a build artifact.
   - `draft`: narrow read-only token over `article-pipeline`, `radar`,
     `tooltempest` and the Habr Anthropic key; no registry-data checkout, no
     write permission, no broad token. Its only output is the attempt files and
     the run record, passed as a build artifact.
   - `deliver`: registry-data write (default `GITHUB_TOKEN`) and the Telegram
     secrets; no Anthropic key, no Collector. It validates the artifact
     (`habr_draft/deliver.py`), commits only `output/habr_draft/<run id>/`, and
     notifies only after a successful push.
   Every checkout except the registry-data write checkout sets
   `persist-credentials: false`. All jobs run the same `article-pipeline` SHA,
   resolved once in `prepare`. GitHub Actions' own artifact upload/download is
   the only channel; no new dependency.
2. **The deliver job treats the artifact as untrusted input.** Only
   `attempt_<N>.md` files and exactly one `run_<run id>.json` are accepted; a
   subdirectory, symlink, foreign name, inconsistent outcome or secret-pattern
   match rejects the whole artifact before anything is staged.
3. **Admission rule for fragments (content-admission for this internal
   pipeline; not a sole-authorship claim and not a legal determination).** A
   fragment is admissible only when the commit's author is an owner identity:
   a GitHub login or an address in `owner_identities` (`mikkiola`,
   `OStroganova`, and the `mikkiola` no-reply address). A display name never
   counts. A commit with any other author, or with none, is excluded
   (`authorship:author_not_owner`, `authorship:authorship_unknown`). The
   committer and the commit message, including `Co-authored-by` trailers, are
   not read, and there is no AI-assistant, bot or per-commit permission policy.
   The basis is the access model above: the one way a third party's commit
   reaches `main` is the owner merging it, and a merge keeps the original
   author, which this check sees. Admitting a third party's work later would
   need its own decision. Disclosure of AI involvement and Habr rule 4 concern
   the article text and stay with the owner's review (ADR-0071).

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Keep one job, set `persist-credentials: false` only | Not chosen. It removes the on-disk token but leaves the App private key, the write credential and the paid stage in one job; the owner decided a hard job boundary. |
| B. Two jobs (prepare+deliver, draft) | Not chosen. It puts the registry-data write credential and the private Collector in one job. |
| C. Pass artifacts through a cache or the registry branch | Not chosen. The owner decided that Actions artifacts are sufficient; a branch write would need the write credential earlier. |
| D. Chosen: three jobs, deliver validates the artifact | Each credential lives in one job; the committing job does not trust the model-handling job's output. |
| E. Admit any commit whose set of identities contains the owner | Not chosen. A commit by a contributor that the owner re-committed (rebase, `git am`) or merged would pass on the owner's committer identity alone, although its author is the contributor. |
| F. Keep the 2026-10-15 form of point 3: five identity categories, trailer parsing, `ai_assistant_policy`, `bot_policy` and a per-commit `fragment_permissions` waiver | Not chosen. It defends against a party who can write commit messages, which needs push access that no one but the owner has. Its AI policy was `allow` and its waiver list empty, so neither refused anything on this data. Its only effect on this data was excluding the `Radar Bot` commits, which the owner has not yet attributed (`[B-077]`). It could not detect third-party code pasted under the owner's name, nor rights an employer may hold. When this ADR was revised, about 220 lines of parsing and about 560 lines of tests carried it. |
| G. No authorship check; rely on the allow-list clearance alone | Not chosen. The owner can merge a contributor's pull request into these public repositories, and the contributor-governance ADRs (ADR-0033 to ADR-0035) anticipate contributors. The author check is the one deterministic backstop for that path and costs one function. |

## Consequences

- `habr_draft/runtime_workflow.example.yml` is three jobs. **Residual:** the
  GitHub App private key (`GH_APP_PRIVATE_KEY`, `GH_APP_ID`) is read by two
  jobs, `prepare` (broad token) and `draft` (narrow token), each as an input of
  the token action only; no Python step receives it. The key is the route to
  the broad token, so the paid-stage job holds a path to it that is closed by
  convention, not by structure. Closing it needs a separate narrow GitHub App
  whose key exists only in `draft`; that choice is the owner's and is not made
  here. `test_workflow_isolation.py` pins the exact set of jobs.
- The `deliver` job's Python steps run code from the pinned reviewed SHA while
  the write credential is on disk in its registry checkout; that residual is
  accepted.
- An unexpected crash in `prepare` or `draft` delivers nothing; handled
  outcomes (including `SYSTEM_FAILURE` and `NO_ELIGIBLE_TOPIC`) always leave a
  run record that `deliver` commits and announces.
- The `OStroganova` account is configured as an owner identity on the owner's
  confirmation of the account. That confirmation covers the account, not
  rights an employer may hold in the 73 `radar` commits written under a
  work-domain address. No code check can establish those rights; the
  question is deferred as a legal one (`[B-078]`). Until the owner records an
  authorship check for `radar`, the whole repository is excluded at stage 1
  (`source_not_cleared`), and those commits predate every daily brief.
- `Radar Bot <radar@gitlab.com>` as author is not an owner identity, so its 31
  `main` commits (13 in `radar`, 18 in `tooltempest`) stay excluded. Whether to
  add its address to `owner_identities` is deferred (`[B-077]`). Two `radar`
  commits authored by the owner and committed by `Radar Bot` are no longer
  excluded, because the committer is not read.
- Residual: a commit authored by the owner that contains a third party's code
  (pasted in, or a squash merge opened by the owner) is admitted. Commit
  metadata cannot show it, and no such case has been observed.
- Residual: the author fields of a merged external commit are written by its
  submitter, so the check does not stop a submitter who puts an owner address
  in them. The owner reviews every pull request she merges and every article
  text before publication, which bounds the impact; the check protects against
  an honest contributor, not against a forged identity. Logins are compared
  exactly (a mis-cased entry excludes the owner's commits, never admits
  another's).

## Confirmation & Revisit

Covered by tests: `habr_draft/test_workflow_isolation.py` (structure of the
example workflow), `habr_draft/test_deliver.py` (artifact gate),
`habr_draft/test_fragments.py` (the author check, including the repository
configuration). Not confirmed on a real run: that requires publishing the
workflow to the runtime repository (owner approval) and inspecting one run's
log for the persisted-credential lines.

Revisit when `actions/checkout`'s default or the App-token action's behavior
changes, when a second account gains write access to an allow-listed
repository, when the owner merges an external contribution into one, when the
owner decides the `Radar Bot` and employer questions (`[B-077]`, `[B-078]`), or
when a commit signature check becomes available to establish authorship by
something stronger than metadata.

**Source.** Owner decisions of 2026-10-15 (job separation, code sources) and of
2026-10-16 (admission rule reduced to an author check, after Claude Code's
investigation of the access model: GitHub API reads of collaborators, pull
requests, workflows and push events, the local commit history of the three
repositories, and the Collector's daily briefs); the runtime workflow run log
of 2026-10-15. No external AI contributed to the decision.
