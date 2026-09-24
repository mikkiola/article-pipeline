---
id: ADR-0055
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0055: Publication Registry state lives on the `registry-data` branch

## Status

Accepted.

## Context & Constraints

Workflow run 35985145119 (Daily LinkedIn Auto-Publish, manual trigger) published a
LinkedIn post, then failed at its "Commit and push Registry output" step:
`remote: error: GH006: Protected branch update failed for refs/heads/main` /
`Changes must be made through a pull request`. The Registry record had been written
and committed on the runner, but the push to `main` was rejected, and a runner's
checkout is discarded when the job ends, so the record was lost. An earlier run
(35971054029) also published and also failed at its commit-and-push step. Both posts went out for the
same `content_id` (`linkedin-2026-09-24`).

Two facts drive the design:

- A runner starts from a fresh checkout every run. The pre-publish check added in
  `daily_publish.py` (`read_record()`, before any publish call) can only see what a
  previous run left in the checkout it starts from. If the record never reaches a
  branch the next run checks out, the check cannot fire.
- `main` is protected: changes must come through a pull request, and the only push
  that reaches it is the owner's admin bypass (ADR-0039). The workflow's bot identity
  has no bypass. Read-only default workflow permissions are overridden by the workflow
  file's own `permissions: contents: write`, so the rejection was branch protection,
  not a missing token scope.

Checked before this decision: the repository has no rulesets (`gh api
repos/.../rulesets` returned an empty list), and the only branches present were `main`
(protected) and `feat/docops-protocol` (unprotected). No other code reads or writes
the Registry output directory; `SPEC.md` describes its location in prose only.

## Decision

Registry files live in `output/` on an unprotected branch named `registry-data`. Code
and the scheduled workflow definition stay on `main`.

- The workflow checks `registry-data` out into a second directory (`registry/`) before
  the publish step.
- The environment variable `REGISTRY_OUTPUT_DIR` tells `publication_registry/writer.py`
  where the Registry files live (`<workspace>/registry/output`). It is read once, at
  import time, when set and non-empty; otherwise the writer's existing default path
  is used. `read_record()` and `write_record()` both use that directory, so the
  pre-publish check reads what the previous run wrote.
- The commit-and-push step runs inside `registry/` and pushes only to
  `registry-data`. `main` never receives a workflow write. A failed push fails the step
  loudly; nothing suppresses it.
- A workflow-level `concurrency` group (`linkedin-daily-publish`, with
  `cancel-in-progress: false`) serializes runs. Two simultaneous runs must not both
  pass `read_record()` before either has written; queuing a second run, rather than
  cancelling it, also avoids killing a publish that is already in progress.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Push the record to `main` with a bypass for the bot | Not chosen. Weakens the protection on the branch that holds all code and governance documents, and requires changing GitHub branch-protection settings. |
| B. Have the workflow open a pull request for each record | Not chosen. State does not persist until the pull request is merged, so the next run still starts without the record; and the approval rule blocks a bot-authored pull request from being merged without the owner. |
| C. Actions cache or workflow artifacts | Not chosen. Both expire and neither is a source of truth; a lost or expired entry would silently re-open the duplicate-publish hole. |
| D. Write the file through the Contents API into `main` | Not chosen. Subject to the same branch protection as a push. |
| E. Chosen — separate unprotected `registry-data` branch, checked out by the workflow | The record persists in git between runs and `main`'s protection stays untouched. Registry records remain one file per `content_id` that the writer never overwrites (ADR-0011). |

## Consequences

- Registry files are no longer written to `main`. The tracked `.gitkeep` under
  `publication_registry/output/` on `main` is now unused by the workflow; the writer's
  default path remains for local runs and tests.
- The first real run is the first confirmation that the default `GITHUB_TOKEN` can push
  to `registry-data`. This is not verified yet: the branch did not exist when this
  decision was made, so a branch-name pattern rule that would cover it could not be
  ruled out from the API beforehand.
- The workflow now fails at its "Checkout registry-data" step if the branch does not
  exist. The branch must be created (one orphan commit holding `output/.gitkeep`)
  before the next scheduled run.
- The publish guard only works from the second run onward. The record of a publication
  already made before this change (for `linkedin-2026-09-24`) is not on `registry-data`,
  so that day's content can still be published again by a run that starts from an
  empty Registry.
- The known reconciliation gap stays open and is not addressed here: if a `block`
  record already exists for a `content_id` and a later run publishes, the final
  `write_record()` of the `pass` record disagrees on `gate_status` and raises
  `PublicationRegistryConflictError` after the post is live.
- Registry history is no longer visible in `main`'s log; it is on `registry-data`.

## Confirmation & Revisit

Confirmed when the first successful scheduled or manual run shows a bot commit on
`registry-data` and no commit on `main`, and a following run for the same date prints
the skip line instead of publishing.

Revisit if the default `GITHUB_TOKEN` cannot push to `registry-data` (for example if a
rule covers that branch name), if Registry state needs to be readable from `main` for
another consumer, or if the block-then-pass reconciliation gap above needs its own
decision.

**Source.** Owner decision, 2026-09-24, following the read-only inspection of workflow
run 35985145119 and the pre-publish Registry check that preceded it.
