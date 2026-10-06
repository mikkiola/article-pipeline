---
id: ADR-0062
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0062: New repository content is classified as a Reusable Product Capability or Customer/Personal Runtime

## Status

Accepted. Records a principle that applies to new content from the date of
acceptance. It does not move, delete or reclassify anything that already
exists in this repository.

## Context & Constraints

This repository is public. The owner's model for it is a reusable product that
is separate from the runtime of one customer or one person's installation.
Content specific to one installation — accounts, folder and deployment
identifiers, credentials, chat settings, schedules, account-specific
orchestration, personal glue scripts — does not belong in a public product
repository.

The repository already holds some installation-specific state and wiring: data
branches written by scheduled workflows, and the definitions of those scheduled
workflows. Nothing before this record stated how to decide where a new script,
workflow, directory or integration belongs.

## Decision

Before creating any new script, workflow, directory or integration, it is
classified as either a Reusable Product Capability or Customer/Personal Runtime,
and the classification and its reason are stated in the task's report.

- A Reusable Product Capability is generic, is configured only through
  environment variables or parameters, and is safe to publish.
- Customer/Personal Runtime is anything specific to one installation.
- Runtime items are not created in this repository, including in hidden or
  git-ignored directories. They live in a private location outside it. This
  record does not name that location.

The rule itself is written in the Unconditional rules of
`docs/CONSTITUTION.md`, where every session reads it at the start.

**Known exception.** The current placement of installation state and wiring in
this repository — data branches and the definitions of scheduled workflows — is
a known exception that awaits a separate decision. This record does not
supersede or amend ADR-0055 or ADR-0060, and it does not decide where that
state and wiring should live.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Do not introduce a rule | Rejected — placement stays a matter of convenience at the moment of creation, and installation-specific content keeps accumulating in a public repository. |
| B. Classify only during review | Rejected — a review sees the finished change. The classification has to be stated before the object is created, when the cheaper placement is still available. |
| C. Put runtime items in a hidden or git-ignored directory inside this repository | Rejected — the object would still live in the product repository, which does not satisfy the boundary. |
| **Chosen — classify before creating, keep runtime outside the repository** | Smallest change that stops new runtime content from entering the repository, without moving anything that already exists. |

## Consequences

- The rule is in `docs/CONSTITUTION.md`; this record is its rationale.
- Every new script, workflow, directory or integration carries a stated
  classification in the report of the task that creates it.
- This record plans no relocation. Existing placement is handled by a separate
  decision.

## Confirmation & Revisit

Applies to new objects from the date of acceptance. Revisit by a separate
decision about the existing exceptions, which, if it changes where installation
state and wiring live, is recorded in a new ADR.

## Source

Owner-directed boundary-hygiene task, 2026-10-02; recorded 2026-10-06 together
with the Constitution rule.
