---
id: ADR-0064
status: Accepted
supersedes: ADR-0055
superseded_by: "ADR-0065 (removal of the workflow file only; all other decisions remain governed by this ADR)"
source_type: verbatim
---

# ADR-0064: The LinkedIn scheduled workflow and its Registry state live in the private runtime repository

## Status

Accepted. Supersedes ADR-0055. Does not supersede or amend ADR-0060 or ADR-0062.

## Context & Constraints

ADR-0055 placed the scheduled LinkedIn workflow definition on this repository's
`main` and the Publication Registry files on this repository's `registry-data`
branch. ADR-0062 later recorded that this placement — data branches and the
definitions of scheduled workflows — is a known exception to the rule that
installation-specific content does not belong in this public repository, and
reserved "a separate decision" about it. ADR-0062 also stated that it does not
name the private location.

The Owner has since moved the LinkedIn wiring to a private repository,
`mikkiola/article-pipeline-runtime`, and decided on 2026-10-08 that this
repository's documentation names it. The decision to name it covers
ARCHITECTURE.md and this record only.

## Decision

**1. Placement.** The scheduled LinkedIn publishing workflow runs from the private
repository `mikkiola/article-pipeline-runtime`. That repository holds the private
execution environment for the public Article Pipeline: the scheduled workflow, its
own copy of the Registry state on a branch named `registry-data`, and the
credentials the workflow needs.

**2. Boundary.** Public product code stays in this repository. Installation-specific
execution state stays in the runtime repository. The two are not mixed: no
runtime content is created in this repository (ADR-0062), and this repository's
documentation describes the runtime repository by name, purpose and boundary only.

**3. What is deliberately not documented here.** Secret values, secret variable
names, file paths inside the runtime repository, and its internal implementation
details. They are not recorded in any public document of this repository.

**4. Supersession scope.** ADR-0055 is superseded for the placement of the
LinkedIn workflow definition and of the Registry state. The reasoning in
ADR-0055 about why Registry state needs a branch of its own, its rejected
alternatives, and the incident that prompted it remain the historical record.
ADR-0060 (Habr Edit Capture) asserts nothing about the LinkedIn workflow and is
unchanged.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Keep the workflow and `registry-data` in this repository (ADR-0055's placement) | Not chosen. ADR-0062 records this placement as a known exception to the product/runtime boundary of a public repository. |
| B. Move them to a hidden or git-ignored directory in this repository | Not chosen. ADR-0062 rejected it: the object would still live in the product repository. |
| C. Chosen — a separate private repository, named explicitly in public documents | The runtime content leaves this repository, as ADR-0062 requires. Naming the repository is the Owner's decision, taken for architectural transparency of a public project; it discloses no runtime contents. |

## Consequences

- This repository's LinkedIn workflow file `linkedin-daily-publish.yml` is still
  present on `main`. In GitHub it is in state `disabled_manually`. Removing the
  file from this repository is not decided here.
- This repository's `registry-data` branch is no longer the live Registry. Its
  last commit is the 2026-10-03 record; records after that date are written to
  the runtime repository's copy.
- The 2026-10-03 Registry record commit `2497d7e` appears in the history of both
  branches. Records after that date were observed only in the runtime
  repository's copy.
- The Habr Edit Capture workflow and its `habr-edit-capture-data` branch are not
  part of this decision. In GitHub that workflow is also in state
  `disabled_manually` in this repository, and the runtime repository has no
  workflow for it. Where Habr placement ends up remains the separate decision
  that ADR-0062 reserved.
- Whether the workflow definition in the runtime repository keeps the
  serialization (`concurrency`) rule from ADR-0055 was not checked and is not
  specified here.

## Confirmation & Revisit

Checked on 2026-10-08 with read-only GitHub queries:

- `mikkiola/article-pipeline-runtime` exists, `visibility: PRIVATE`, with branches
  `main` and `registry-data`.
- It has one workflow, "Daily LinkedIn Auto-Publish", state `active`.
- Two `schedule`-event runs of that workflow concluded `success`: `37562871102`
  (2026-10-07) and `37719863856` (2026-10-08), both at head
  `019c9429297b5f050c5322b48ac269c60a70e6f3`. Each is followed on its
  `registry-data` branch by a commit `chore(publish): daily LinkedIn Registry
  record <date>` (2026-10-07, 2026-10-08).
- In this repository the workflow "Daily LinkedIn Auto-Publish" is `disabled_manually`.

Not checked: the content of the two Registry records (for example their gate
status), the contents of the runtime workflow, and when the workflow in this
repository was disabled.

Revisit if the Habr placement decision changes where installation state lives,
if the workflow file in this repository is removed, or if the runtime
repository's boundary is changed.

**Source.** Owner decision, 2026-10-08, naming `mikkiola/article-pipeline-runtime`
in ARCHITECTURE.md and this record; state of the migration read from GitHub on
the same date as listed above.
