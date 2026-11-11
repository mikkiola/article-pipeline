---
id: ADR-0075
status: Accepted
supersedes: null
superseded_by: null
source_type: inferred
---

# ADR-0075: Retire the Tier 2 Doc-Sync and the Legacy doc_sync Modules

## Status

Accepted by the Owner, 2026-11-11. Supersession is partial and specified
below; the file-level fields stay null, following the point-level precedent of
ADR-0073. The superseded ADRs remain intact.

## Context & Constraints

ToolTempest ADR-0019 defines how a path of an installed root leaves the
manifest. At ToolTempest commit `d2172e7`, `MANIFEST.txt` has no line for
`scripts/doc_sync.py`, `scripts/doc_sync_tier2.py` or
`schemas/execution-record.schema.json`
(`git show d2172e7:MANIFEST.txt | grep -c "doc_sync\|execution-record"` prints 0).
A lock that declares a path the pinned manifest does not install fails
closed, so repinning here needs a new declaration. The Owner decided the
repin across the removal on 2026-11-11.

Observation at commit `286b137` of this repository:
`git grep -n -I -E "doc_sync|execution-record|apply_tier2_sync|TIER2_DOCS" 286b137 -- . ':!docs/adr' ':!docs/BACKLOG.md' ':!.tempest'`
matches only `.tooltempest.lock`, `.gitignore`, `README.md`, `CONTRIBUTING.md`,
`docs/ARCHITECTURE.md` and `.claude/skills/session-end/SKILL.md`; no hook,
workflow or check matches. The only caller was the structural fact-sync step
of the `/session-end` skill, which called `apply_tier2_sync()`.
The reconciliation workflow that called the same module was retired by
ADR-0073.

## Decision

1. This repository repins ToolTempest to the commit recorded in
   `.tooltempest.lock`, which declares only the pair path and sha256 of
   `scripts/docops.py`.
2. Nothing tracked here imports, calls or is configured to run the retired
   modules. The `/session-end` skill no longer has the structural fact-sync
   step. The gitignore entries and the README, ARCHITECTURE and CONTRIBUTING
   text that existed only for the modules are removed.
3. The Constitution is unchanged. The `Syncs:` trailer remains a project rule
   that no skill, hook or check reads.
4. ADR-0073 item 4 (keep `doc_sync.py` and `doc_sync_tier2.py`) is superseded.
5. ADR-0033 points 1 to 5, which describe the reconciliation workflow's use
   of the Tier 2 module, and ADR-0034's description of the
   `apply_tier2_sync()` call are superseded to the extent that they require
   the Tier 2 module. ADR-0034's decision that contributors supply their own
   document updates remains.
6. No decision of ADR-0032 is superseded. Its mentions of `doc_sync.py`
   describe a module that is no longer installed.

## Alternatives & Rationale

| Option | Verdict | Why |
|---|---|---|
| Keep the modules vendored | Rejected | The pinned manifest no longer installs them. |
| Drop the lock declaration and rely on the install receipt | Not chosen | The Owner chose to re-declare `scripts/docops.py`, which keeps one independent hash in this repository's Git history. |
| Edit ADR-0032, 0033, 0034 and 0073 in place | Rejected | An accepted decision changes only by a superseding record. |

## Consequences

- ToolTempest does not delete or report copies of the retired files installed
  earlier. ADR-0019 puts their deletion on the consumer at this repin. No
  ignore rule covers them after this change, so each copy shows as untracked
  until it is deleted and must not be committed.
- Constitution rule AP-6 requires a `Syncs: <path>` trailer and says
  `/session-end` reads it. Nothing reads it now. Whether to change AP-6 is an
  open Owner decision; the Constitution is not edited here.
- Historical records (`.tempest/runs/`, BACKLOG entries) keep their mentions.

## Confirmation & Revisit

In a worktree created from `origin/main` at `286b137` with this lock,
`scripts/tooling.py materialize --source <ToolTempest clone at d2172e7>`
(dry run) planned 23 creations and exited 0; `--apply` exited 0 and reported
23 files written and verified; `verify` exited 0 with local integrity and
upstream provenance `ok`.
Revisit if a consumer needs a Tier 2 style snapshot-and-apply flow again.

**Source.** The Owner's instruction of 2026-11-11 (DocOps Stage 8). No external
AI cross-check was made.
