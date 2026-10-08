---
id: ADR-0065
status: Accepted
supersedes: "ADR-0064 (removal of the workflow file only)"
superseded_by: null
source_type: verbatim
---

# ADR-0065: The disabled LinkedIn workflow file is removed from this repository

## Status

Accepted. Supersedes ADR-0064 on one point only: whether the LinkedIn workflow
file stays in this repository. Every other decision in ADR-0064 (placement of the
workflow and the Registry state in the private runtime repository, the boundary,
and what is deliberately not documented) remains in force. Does not supersede or
amend ADR-0055, ADR-0060 or ADR-0062.

## Context & Constraints

ADR-0064 recorded that the scheduled LinkedIn workflow runs from the private
runtime repository, and that this repository's copy of the workflow file was still
present on `main` in state `disabled_manually`. It stated that removing the file
"is not decided here" and listed the removal of the file as a revisit trigger.

State read from GitHub and from this repository on 2026-10-08:

- The workflow "Daily LinkedIn Auto-Publish" is `disabled_manually` in this
  repository. Its last run here was on 2026-10-06; no run is recorded after that.
- No other workflow in this repository references the file, the workflow name, or
  the credentials the workflow used.
- Nothing in this repository writes to this repository's `registry-data` branch
  any more; its last commit is the 2026-10-03 record.
- ADR-0064 records two successful `schedule` runs of the workflow in the runtime
  repository. They were not re-checked for this record.

Not checked for this record: the private runtime repository itself.

## Decision

**1. The file is removed.** `.github/workflows/linkedin-daily-publish.yml` is
removed from `main` of this repository, through a pull request.

**2. Scope.** This decision covers the workflow file only. It does not decide, and
changes nothing about:

- the repository secrets of this repository;
- this repository's `registry-data` branch;
- the Habr Edit Capture workflow and its `habr-edit-capture-data` branch;
- the private runtime repository.

Each of these remains a separate decision.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Keep the disabled file in `main` | Not chosen. The file is a definition of a scheduled workflow that this repository no longer runs; ADR-0062 records that such definitions are a known exception to the product/runtime boundary of a public repository. A disabled file can be enabled again in one click and would run against this repository. |
| B. Chosen — remove the file, change nothing else | Removes the last runtime definition from this repository without touching state that other records still cite or that cannot be restored. |
| C. Remove the file and the repository secrets together | Not chosen. A deleted secret value cannot be read back from GitHub, so the step cannot be undone. It depends on a verification of the runtime repository that this record does not contain. |

## Consequences

- This repository no longer contains a LinkedIn workflow definition. ARCHITECTURE.md
  is updated accordingly.
- ADR-0064's statement that the file "is still present" describes the state when it
  was written. It is not rewritten.
- The workflow's earlier runs, and the earlier records ADR-0055 and ADR-0064, remain
  the historical record of how it ran here.
- Comments in the Habr Edit Capture workflow and code that name the removed file are
  not changed by this decision.
- The repository secrets remain as they are until a separate decision.

## Confirmation & Revisit

Checked on 2026-10-08 with read-only queries: workflow state (`gh workflow list
--all`), the workflow's run list, a search of this repository for references, and
the commit listing of `registry-data`. The removal is confirmed by the pull request
that carries this record: the file is absent from `main` after the merge.

Revisit if the workflow has to run from this repository again; in that case the
file would be restored by a new record, not by reverting this one silently.

**Source.** Owner decision, 2026-10-08, resolving the point ADR-0064 left open;
state read from GitHub and this repository on the same date as listed above.
