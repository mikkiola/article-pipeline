# 0028 — Client independence and update lifecycle for shared tooling

## Status
Accepted. Manual lock+delivery path implemented and confirmed
(`mikkiola/article-pipeline` commit `3d4ad09`). CLI adapter and
discovery mechanism remain unbuilt — this record specifies their
architectural contract only, not their implementation.

## Context

`mikkiola/tooltempest` (0026) needs a defined relationship with the
tools that consume it (Claude Code today; potentially Cursor, Codex, or
others later) that does not couple the canonical repository to any one
of them, and a defined way to handle version updates without silent
behavior changes.

## Decision

The canonical repository stays entirely client-agnostic — it contains
only `skills/spec/SKILL.md`, `skills/verify/SKILL.md`, and
`rules/drift-control.md`, with no client-specific files or logic of any
kind. Client-specific differences are isolated in a separate, lightweight
CLI adapter layer, not built into the canonical repository. Detecting
that a new version exists (discovery) may happen automatically;
installing or activating that version never happens automatically — it
always requires an explicit, human-triggered action. Silent auto-update
is not permitted under any circumstance.

## Options considered

**A — Client-specific core.** Rejected — ties the canonical source to
one particular AI client's conventions; migrating to a different client
would require either duplicating the canonical layer or rewriting the
existing contract. Creates coupling between the infrastructure layer and
whichever tool happens to be running it, and creates technical debt
starting in version 1.

**B — Client-agnostic core plus a separate adapter layer (chosen).** One
canonical source stays client-agnostic; per-client differences are
isolated in the adapter layer, not in the canonical repository.

**C — A separate, independent copy of the tooling per client.** Rejected
— produces multiple sources of truth and risks silent divergence between
clients, which directly repeats, at larger scale, the exact problem that
motivated splitting tooling out of `~/.claude/` into its own repository
in the first place (see 0026's context).

## Constraints

- Version identity: full 40-character Git commit SHA, per 0026. A tag is
  a mutable alias, never a source of truth.
- Each consumer records its pinned version in `.tooltempest.lock` — the
  lock file name specified by this record. The prior text of 0027 named
  it `.claude-tooling.lock`; 0027's original text is not edited
  retroactively (Immutable Lineage). `.tooltempest.lock` is the correct,
  current name for implementation, established by this record.
- Silent auto-update is prohibited without exception.
- Discovery of a new version may run automatically; installation and
  activation require an explicit action every time.
- Rollback is a deterministic change of the pinned SHA in the lock file.
- Offline recovery is guaranteed only for a SHA already present in the
  local cache (`~/.cache/tooltempest/<SHA>`) — not a guarantee of full
  offline reproducibility from zero.
- Version 1 of ToolTempest requires no runtime dependencies in the
  canonical core.
- No client-specific logic is placed in the canonical core.
- This record does not itself build the CLI adapter — only its
  architectural contract (discovery is distinct from activation; the
  canonical repository stays client-agnostic) is fixed here. Designing
  a minimal version-1 adapter is separate future work.

## Rejected
See Options A and C above. Also explicitly rejected: silent auto-update
in any form (breaks deterministic consumer state, creates stealth
behavior drift); a mutable tag as version identity (a tag can point to a
different commit without its name changing); any promise of guaranteed
offline recovery on a clean machine with no network and no local cache
(this cannot honestly be promised).

## Consequences

ToolTempest remains a plain open-source-style core repository — no paid
infrastructure, no Organization account, no registry or backend. This
does not architecturally foreclose a future hosted registry, fleet
management, or policy synchronization layer, but does not build one now
either. A separate adapter-layer boundary is introduced as a result of
this decision. Tooling lifecycle is split into three distinct stages:
discovery → explicit installation/activation → rollback. A local cache
directory (`~/.cache/tooltempest/<SHA>`) is implied by the recovery
constraint above but is not itself built by this record — that is CLI
adapter work, still pending. Any future validation harness for this
tooling should check, at minimum: SHA pinning is respected, updates
require an explicit action, rollback works, and client-adapter behavior
matches the contract above.

**Boundary, fixed by this record:** Article Pipeline is responsible for
its own domain logic, project memory, specifications, decisions, state,
and its integration with ToolTempest. ToolTempest is responsible for
client-agnostic shared primitives, their version identity, the delivery
contract, and the lifecycle contract for shared tooling. Article
Pipeline's project memory is never migrated into ToolTempest — ToolTempest
does not become a second source of truth for Article Pipeline's
architecture.

## Validation
Confirmed for the manual path only: `mikkiola/article-pipeline` commit
`3d4ad09` created `.tooltempest.lock` and `scripts/sync-tooling.sh` (a
manual, zero-dependency sync helper — explicitly not the CLI adapter
described above), ran it successfully end to end (exit code 0), verified
the three synced files byte-for-byte identical against the pinned-commit
source, and confirmed a boundary grep across the three synced primitives
found zero mentions of `article-pipeline`, `Claim Extraction`, `Evidence
Package`, or `Atom Selector` — the canonical repository stayed
domain-agnostic as required. CLI adapter and discovery mechanism remain
entirely unvalidated because they remain unbuilt.

## Reversal condition

Revisit if implementing a second AI client shows that the adapter layer
cannot isolate client-specific differences without breaking the
semantics of the canonical primitives, or does so only at
disproportionate complexity cost. An additional signal: if, after a
second client is added, most of the canonical core starts filling with
conditional client-specific branches, that is itself a sign this
decision needs revisiting. Until such evidence exists, this decision
stands — it does not quietly revert to option A or C in the meantime.

## Source

Continues 0026 (canonical source and version identity) and 0027 (lock
and delivery contract). Originally formalized in an external review
brought by the owner in an "external architectural reviewer" role;
verified line-by-line against the architect's own prior record of this
decision — one discrepancy was found and corrected (the lock file
rename is this record's decision, not inherited from 0027's original
text; 0027's text is explicitly not rewritten after the fact). The
principle of client independence and the prohibition on stealth behavior
drift were both stated directly by the project owner.
