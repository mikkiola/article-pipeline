---
id: ADR-0026
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0026 — Canonical source and version identity for shared tooling

## Status

ACTIVE. Implementation: consumer-side lock+delivery path closed (commit
`3d4ad09` in `mikkiola/article-pipeline`); the canonical repository
itself was created separately — see ARCHITECTURE.md for current state
at time of reading.

## Context & Constraints

Shared tooling was being used by two independent projects
(`article-pipeline`, `radar`) from a single unversioned copy at
`~/.claude/`, with no version history and no way to know which version
either project was actually running. The project is scaling toward 8+
independent repositories, each expected to consume the same shared
primitives — a machine-local, unversioned dependency does not scale past
one machine or one developer. Option C required the fewest unproven
assumptions relative to A and B at equal functionality: no new tooling
category, no new runtime dependency, and version identity that is exact
rather than approximate.

Version identity = full 40-character Git commit SHA; tags are not a
source of truth. `mikkiola/tooltempest` must remain client-agnostic — no
Article-Pipeline-specific or Radar-specific content. Public repository,
personal account (not an Organization). No paid infrastructure.

## Decision

Shared tooling (`/spec` interview skill, `/verify` validation skill,
`drift-control.md` deviation-tracking rule) gets its own independent Git
repository: `mikkiola/tooltempest`. Version identity is the full
40-character Git commit SHA. A Git tag is treated as a mutable
human-readable alias, not a source of truth.

## Alternatives & Rationale

A — keep tooling in `brain.git`. B — package manager / installer script
pattern (e.g. install.sh fetched via curl). C — independent Git
repository, pinned by full commit SHA (chosen).

C.

A — `brain.git` already hosts Drift/Collision Engine and the Brain
knowledge graph; 0001 already established that Article Pipeline should
not couple its runtime behavior to Brain's repository, and extending
that coupling to shared tooling repeats the same mistake at a different
layer. B — adds a runtime dependency (script execution, network fetch at
install time) for no benefit over a plain Git checkout at a pinned SHA,
and does not solve version identity unless it also pins a SHA, at which
point it is a thin wrapper around option C anyway.

## Consequences

A third repository now exists on the machine dedicated to
infrastructure, not project logic — treated as justified scaling cost (9
repositories exist at time of writing, 8+ personal projects planned),
not an unnecessary repository for a single file. Every consuming project
needs its own delivery mechanism to pull a pinned version in — see 0027.

## Confirmation & Revisit

Confirmed by later implementation on the consumer side — see 0028 and
the commit it references.

Revisit if a second, unrelated shared-tooling need emerges that this
repository cannot reasonably absorb without becoming project-specific
itself — at that point, evaluate splitting rather than overloading one
repository with unrelated tool families.

**Source.** Build-vs-reuse check returned negative for existing patterns (brain.git,
dotfiles convention, package manager, install script). Owner-confirmed
scope: 9 repositories on the machine at time of decision, 8+ personal
projects planned.
