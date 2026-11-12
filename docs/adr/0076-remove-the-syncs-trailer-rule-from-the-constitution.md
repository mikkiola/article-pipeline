---
id: ADR-0076
status: Accepted
supersedes: null
superseded_by: null
source_type: inferred
---

# ADR-0076: Remove the Syncs Trailer Rule from the Constitution

## Status

Accepted by the Owner, 2026-11-11. Supersession is partial and specified
below; the file-level fields stay null, following the point-level precedent of
ADR-0073 and ADR-0075. The superseded ADRs remain intact.

## Context & Constraints

The Constitution rule AP-6 requires a `Syncs: <path>` trailer on a commit that
changes a fact in `docs/ARCHITECTURE.md`, `docs/ROADMAP.md` or `README.md`, and
says `/session-end` reads the trailers. The trailer gave a Tier 2 doc-sync
step something to read. ADR-0075 retired that step and recorded that the
trailer "remains a project rule that no skill, hook or check reads", and left
the change of AP-6 as an open Owner decision. The Owner decided on 2026-11-11
that the dead `Syncs:` and `/session-end` statements are removed from the
Constitution.

Observation at commit `56e9023`:

- `git grep -n -I 'Syncs' 56e9023 -- . ':!docs/adr' ':!docs/BACKLOG.md'`
  matches only `docs/CONSTITUTION.md` (AP-6).
- `git grep -n -I -E 'trailers|Syncs' 56e9023 -- scripts .github .claude CLAUDE.md`
  shows that the only trailer parsing is the `/session-end` skill, and it
  reads `Closes` only (`trailers:key=Closes`).
- `.tooltempest.lock` pins ToolTempest `a55d6c0`; `git grep -n -i syncs a55d6c0 -- scripts rules skills docs ':!docs/adr'`
  in ToolTempest prints nothing, so the pinned checker and the universal
  rules do not read or require the trailer.

Neither the Constitution nor an Accepted ADR defines AP-6 as a decision. The
only Accepted decision point that states the trailer is ADR-0075 Decision
point 3.

## Decision

1. The Constitution no longer requires, promises or describes the `Syncs:`
   trailer. Rule AP-6 is deleted. Its ID is not reused and the other rule IDs
   are not renumbered.
2. `/session-end` reads `Closes:` trailers only. The `Closes:` trailer rule
   and the skill do not change.
3. This ADR supersedes ADR-0075 Decision point 3 ("The Constitution is
   unchanged. The `Syncs:` trailer remains a project rule…"). ADR-0074's
   statement in its Consequences that the `Syncs:` trailer stays a project rule
   is superseded to the same extent. Both ADRs stay `Accepted`.

## Alternatives & Rationale

| Option | Verdict | Why |
|---|---|---|
| Keep AP-6 | Rejected | It binds every commit to an obligation that nothing reads or checks, and it states a `/session-end` behavior that does not exist. |
| Implement a reader for `Syncs:` | Rejected | No requirement asks for it. The Owner chose removal. Under AP-12 and AP-13 a judgment-based process rule does not get a script check. |
| Keep AP-6 and mark it retired in place | Rejected | The Constitution carries no history or dated notes; Git and the decision records hold it. |

## Consequences

- A commit that changes `docs/ARCHITECTURE.md`, `docs/ROADMAP.md` or
  `README.md` needs no `Syncs:` trailer. A commit with one is still valid; no
  tool reads it.
- Dated entries in `docs/BACKLOG.md` and the bodies of Accepted ADRs keep their
  mentions of the trailer. They are history.
- The `Closes:` trailer, the `/session-end` skill, and the push-time warning of
  `scripts/check-doc-pairing.sh` are unchanged.

## Confirmation & Revisit

After the change, `git grep -n -I 'Syncs' HEAD -- . ':!docs/adr' ':!docs/BACKLOG.md'`
prints nothing. The commit that adds this record carries the checks it ran.
Revisit if a tool again needs commit-time evidence of which documents a commit
updated.

## Source

The Owner's decision of 2026-11-11, executed in a Claude Code session. Claude
Code drafted the wording, so `source_type` is `inferred`. No external AI
cross-check was made.
