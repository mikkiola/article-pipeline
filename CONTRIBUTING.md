# Contributing

## Documentation updates

If your pull request changes something that affects one of this
project's four tracked documents, include that document update in
the same PR:

- **`docs/ARCHITECTURE.md`** — if your change affects a component's
  status, validation, or commit reference in the component table.
- **`docs/BACKLOG.md`** — if your change closes a tracked item, or
  should add a new one.
- **`docs/ROADMAP.md`** — if your change affects sequencing or the
  current phase plan.
- **`README.md`** — if your change affects what the project does or
  how to use it.

Write the update in the format the project's existing entries already
use in each file — match the surrounding style rather than inventing
a new one.

### Why this matters

Your PR supplies the document updates directly (ADR-0034). Include
them before review and merge: no post-merge workflow generates,
applies, or proposes them. The obsolete reconciliation workflow was
retired by [ADR-0073](docs/adr/0073-retire-post-merge-reconciliation.md).
The existing CODEOWNERS and `main` branch protection remain the
pre-merge review gate for `docs/BACKLOG.md` and `docs/ROADMAP.md`.

### Current status: process expectation, not yet enforced

This project's automated pre-commit/pre-push checks do not currently
verify that a PR includes the doc updates it needs (confirmed during
this project's 2026-08-19 session; see `docs/BACKLOG.md`). Until that
gap is closed, following this requirement is a process expectation,
not something the tooling will catch for you — please check it
yourself before opening a PR.
