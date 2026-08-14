# 0026 — Canonical source and version identity for shared tooling

## Status
Accepted. Implementation: not started at time of writing (superseded —
see commit `3d4ad09` in `mikkiola/article-pipeline`, which closes the
consumer-side lock+delivery path; the canonical repository itself was
created separately, see ARCHITECTURE.md for current state).

## Context

Shared tooling (`/spec` interview skill, `/verify` validation skill,
`drift-control.md` deviation-tracking rule) was used by two independent
projects (`article-pipeline`, `radar`) from a single unversioned copy at
`~/.claude/`. This tied both projects' tooling behavior to one
machine-local file with no version history, no changelog, and no way to
know which version either project was running.

The project is scaling toward 8+ independent repositories, each
expected to consume the same shared primitives. A machine-local,
unversioned dependency does not scale past one machine or one developer.

## Decision

Shared tooling gets its own independent Git repository:
`mikkiola/tooltempest`. Version identity is the full 40-character Git
commit SHA. A Git tag is treated as a mutable human-readable alias, not
a source of truth — a tag can be moved to point at a different commit
without changing its name.

## Options considered

**A — Keep tooling in `brain.git`.**
Rejected: `brain.git` already hosts Drift/Collision Engine and the Brain
knowledge graph. Prior decision D-001 established that Article Pipeline
should not couple its runtime behavior to Brain's repository. Extending
that coupling to shared tooling repeats the same mistake at a different
layer.

**B — Package manager / installer script pattern (e.g. a `install.sh`
fetched via curl).**
Rejected: adds a runtime dependency (script execution, network fetch at
install time) for no benefit over a plain Git checkout at a pinned SHA.
Does not solve version identity — an installer script has the same
"what version did I actually get" problem unless it also pins a SHA,
at which point it is a thin wrapper around option C.

**C — Independent Git repository, pinned by full commit SHA (chosen).**
Selected because it required the fewest unproven assumptions relative
to the other two options at equal functionality: no new tooling
category, no new runtime dependency, and version identity is exact
rather than approximate.

## Constraints

- Version identity = full 40-character Git commit SHA. Tags are not a
  source of truth.
- `mikkiola/tooltempest` must remain client-agnostic — no
  Article-Pipeline-specific or Radar-specific content.
- Public repository, personal account (not an Organization). No paid
  infrastructure.

## Rejected

- Client-specific fork per consuming project — rejected as it
  reintroduces the original problem (divergent, unversioned copies) in
  a different shape.
- Tag-based versioning as the primary identity — rejected because a tag
  can silently move.

## Consequences

- A third repository now exists on the machine dedicated to
  infrastructure, not project logic. This is treated as justified
  scaling cost (9 repositories exist at time of writing, 8+ personal
  projects planned), not an unnecessary repository for a single file.
- Every consuming project needs its own delivery mechanism to pull a
  pinned version in — see D-027.

## Reversal condition

Revisit if a second, unrelated shared-tooling need emerges that this
repository cannot reasonably absorb without becoming project-specific
itself — at that point, evaluate splitting rather than overloading one
repository with unrelated tool families.

## Source

Build-vs-reuse check returned negative for existing patterns
(`brain.git`, dotfiles convention, package manager, install script) —
see Options considered above. Owner-confirmed scope: 9 repositories on
the machine at time of decision, 8+ personal projects planned.
