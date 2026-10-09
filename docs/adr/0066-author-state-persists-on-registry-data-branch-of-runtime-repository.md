---
id: ADR-0066
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0066: The Author's identity-continuity state persists on the runtime repository's registry-data branch

## Status

Accepted on 2026-10-09 as a decision. The decision is not yet confirmed by a real
run: see Confirmation & Revisit, which is open. Does not supersede or amend
ADR-0059, ADR-0062, ADR-0064 or ADR-0065.

## Context & Constraints

ADR-0059 (Decision point 6) wires identity continuity as a generation input:
`author/identity_state.py` persists `identity_state.json` and `recent_posts.json`
under `author/state/` and the daily publish loads both before every generation.
ADR-0064 placed the scheduled LinkedIn workflow, and the Registry state, in the
private repository `mikkiola/article-pipeline-runtime`.

State read on 2026-10-09:

- Before this decision, `STATE_DIR` in `author/identity_state.py` was fixed to the
  `author/state/` directory inside the checkout, with no override.
- The scheduled workflow in `mikkiola/article-pipeline-runtime` checks out
  `mikkiola/article-pipeline` at `main` on every run, so that directory starts
  empty on every run and is discarded when the run ends. Every scheduled run
  therefore reads an empty `recent_posts`, and no history is kept.
- The Registry survives between runs because the product code reads the directory
  named by the `REGISTRY_OUTPUT_DIR` environment variable, the workflow points it
  at a checkout of the `registry-data` branch, and the workflow commits that
  checkout back (ADR-0055 introduced the branch; ADR-0064 moved it to the runtime
  repository).
- `author/state/` was not git-ignored and was never committed in either
  repository. The `registry-data` branch of the runtime repository held only the
  Registry output directory and a placeholder file.
- ADR-0062 defines product code as configured only through environment variables
  or parameters, and records that runtime content does not belong in this public
  repository. `recent_posts.json` holds the text of real published posts.

## Decision

**1. Same mechanism as the Registry.** `author/identity_state.py` reads the state
directory from the `AUTHOR_STATE_DIR` environment variable when it is set and
non-empty, and otherwise keeps the previous default. The variable is read once, at
import time, like `REGISTRY_OUTPUT_DIR`.

**2. Same branch, same commit.** In the runtime repository the scheduled workflow
points `AUTHOR_STATE_DIR` at a directory of the `registry-data` checkout, next to
the Registry records, and commits it in the same commit and the same push as the
Registry record. Only the scheduled job writes it back.

**3. This repository holds no state.** `author/state/` is git-ignored here, so a
local run cannot add real post text to this public repository (ADR-0062). The
runtime repository is private.

**4. What is deliberately not documented here.** As in ADR-0064: secret values,
secret variable names, file paths inside the runtime repository, and its internal
implementation details.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Link `author/state` to a directory of the registry checkout from the workflow | Not chosen. It needs no product change, but couples the workflow to the internal layout of `author/` without any declared contract. |
| B. A separate branch or a separate commit step for the state | Not chosen. It doubles the push surface and loses atomicity with the Registry record: a run could persist the record but not the state, or the reverse. |
| C. Chosen — an environment-variable override in the product code, the state on `registry-data` | Reuses the existing, ADR-0062-sanctioned product/runtime seam and the existing persistence path; one commit carries both. |

Order independence (the principle of ADR-0056): product code that ignores the
variable behaves as before, and a workflow that does not set the variable leaves
the product code on its previous default. Neither side breaks the other when it is
deployed first.

## Not decided here

These stay as they were and are not changed by this record:

- the writer that would populate `identity_state.json` (`docs/BACKLOG.md`, `[B-070]`);
- the length limit on the list of recent posts (`RECENT_POSTS_LIMIT`) and any
  separate archive file; the git history of the persisted file is the only history
  this record provides;
- the `PublicationRecord` schema;
- `[B-069]`, and the `claim_id` rule of ADR-0054;
- the Registry gap for the automation-only-day outcome;
- any rewrite or deletion of existing records on either `registry-data` branch.

## Consequences

- Once the runtime workflow sets the variable, `recent_posts.json` written by one
  scheduled run is available to the next. Until then, every run still starts with
  an empty list.
- Historical post text is not present in the repository's persisted state.
  Recovery from external posts or workflow logs has not been investigated and is
  out of scope for this change. No historical backfill is included.
- The persisted file lives in a private repository; the real post text is not
  published through this decision.
- A day on which no post is published (gate block, automation-only day, skip)
  writes no state, and the workflow must tolerate that without failing the
  Registry commit.

## Confirmation & Revisit

**Pending. Not confirmed.** At the time of writing the product change is committed
locally and the runtime workflow is unchanged. This section is to be filled in
after two consecutive real scheduled or manually dispatched publishes on different
brief dates, each followed by a commit on the runtime repository's `registry-data`
branch, by the literal difference of `recent_posts.json` between the two commits:
the second must contain the first run's post text as an earlier entry, plus the new
one; and the second run's log must show the earlier post as loaded. Until that
evidence is recorded here, no document may state that the state is persisted per
run.

Revisit if the Registry's persistence mechanism changes, if the runtime repository's
boundary changes, or if the identity-state writer (`[B-070]`) needs a different
home for its data.

**Source.** Owner task (Handoff 3), 2026-10-09; the product code and the runtime
workflow read directly on that date. No external AI contributed.
