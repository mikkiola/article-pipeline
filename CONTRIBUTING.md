# Contributing

## Documentation updates

If your pull request changes something that affects one of this
project's three tracked documents, include that document update in
the same PR:

- **`docs/ARCHITECTURE.md`** — if your change affects a component's
  status, validation, or commit reference in the component table.
- **`docs/BACKLOG.md`** — if your change closes a tracked item, or
  should add a new one.
- **`docs/ROADMAP.md`** — if your change affects sequencing or the
  current phase plan.

Write the update in the format the project's existing entries already
use in each file — match the surrounding style rather than inventing
a new one.

### Why this matters

After your PR merges, a reconciliation workflow (see
`docs/adr/0033-contributor-governance-post-merge-reconciliation.md`
and `docs/adr/0034-contributor-supplied-doc-updates.md`) reads your
PR's merged content directly to apply and propose these document
updates. It does not generate or infer document updates on its own —
if your PR is missing a required update, the reconciliation will be
incomplete or incorrect.

### Current status: process expectation, not yet enforced

This project's automated pre-commit/pre-push checks do not currently
verify that a PR includes the doc updates it needs (confirmed during
this project's 2026-08-19 session; see `docs/BACKLOG.md`). Until that
gap is closed, following this requirement is a process expectation,
not something the tooling will catch for you — please check it
yourself before opening a PR.
