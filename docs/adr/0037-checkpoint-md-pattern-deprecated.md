---
id: ADR-0037
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0037: CHECKPOINT.md Pattern Deprecated — Inline Milestones Only

Relates to: `docs/CONSTITUTION.md`'s SPEC.md location/lifecycle rule
(2026-08-20), which this ADR extends to the pattern CHECKPOINT.md's
absence of an equivalent rule left unresolved. Does not extend or edit
any prior ADR.

## Status

Accepted

## Context & Constraints

`scripts/verify.py`'s component discovery (`classify()`) treated a
paired `CHECKPOINT.md` as a VC-source pattern with unconditional
priority over a SPEC.md's own inline Milestones section — if
`CHECKPOINT.md` existed at all next to a SPEC.md, it was chosen,
regardless of whether the SPEC.md also had a well-formed inline
Milestones section. This was confirmed live, not hypothetically: the
DocOps SPEC.md committed as `dcb84e4` (2026-08-20) had its own
well-formed inline Milestones section silently bypassed by this
priority rule for two full commits (`dcb84e4`, `367e8b2`), because a
stale root `CHECKPOINT.md` — entirely about the closed Evidence Package
component, unrelated to either SPEC.md's actual topic — happened to
still exist at the same path.

This is the second time a CHECKPOINT.md/SPEC.md pairing orphaned in this
project (`docs/BACKLOG.md`'s "CHECKPOINT.md orphaning recurs" entry,
2026-08-20, is the first — filed as a pointer, not resolved, pending
this decision). `docs/CONSTITUTION.md` already has a location/lifecycle
rule for SPEC.md itself (single root location, overwritten by a new
`/spec` session, history via `git log`); CHECKPOINT.md had no equivalent
rule, and its priority-over-inline-content behavior made a stale copy
actively harmful, not merely orphaned clutter.

Option A is the only one that removes the actual defect — a stale file
silently overriding correct, current content — rather than managing its
symptom (orphaning) or its likelihood (priority order). A single VC-source
pattern also matches this project's actual practice already: every
`/spec`-produced SPEC.md in this repo (`dcb84e4`, this consolidated one)
already uses inline Milestones; CHECKPOINT.md's only real content on
disk was the pre-`/spec`-skill Evidence Package tracking, now historical.

Does not retroactively rewrite the deleted `CHECKPOINT.md`'s content —
recoverable via `git log --follow -- CHECKPOINT.md` per the same
precedent already established for `SPEC.md`. Does not change
`docs/CONSTITUTION.md`'s SPEC.md location/lifecycle rule itself — this
ADR closes the parallel question for CHECKPOINT.md by removing the
pattern rather than by mirroring that rule. Does not affect
`~/.claude/skills/spec/SKILL.md`'s own template, which already produces
inline Milestones sections, not CHECKPOINT.md files.

## Decision

`CHECKPOINT.md` is deprecated as a VC-source pattern entirely, not
given a parallel lifecycle rule. SPEC.md's own inline `## Milestones`
section (checkbox lines with description text, already the pattern this
project's own `/spec`-produced SPEC.md files use) becomes the only
supported VC-source pattern. `scripts/verify.py`'s `classify()` no
longer checks for `CHECKPOINT.md`'s existence at all; the root
`CHECKPOINT.md` file itself is deleted in the same commit as this ADR.

Rejected the alternative of giving CHECKPOINT.md the same
single-location/overwrite rule SPEC.md already has (Option B below):
that would fix the orphaning but not the priority bug — a correctly-
overwritten CHECKPOINT.md would still silently override a SPEC.md's own
inline content the moment the two drifted even briefly out of sync
(e.g., mid-edit, or a `/spec` session that updates SPEC.md before its
paired CHECKPOINT.md catches up). Removing the second pattern removes
the whole class of bug structurally, rather than managing it with a
second lifecycle rule that mirrors, and could still fail the same way
as, the first.

## Alternatives & Rationale

| Option | Pros | Cons | Risks |
|---|---|---|---|
| A. Chosen: deprecate CHECKPOINT.md, inline Milestones only | Removes the priority-override bug structurally, not just the orphaning; one VC-source pattern instead of two to keep consistent; matches what `/spec`-produced SPEC.md files already do in practice | Loses CHECKPOINT.md's per-block field format (`verify:`/`done-when:`/`status:`) as a distinct structure — inline Milestones checkboxes carry less per-item structured metadata | A future SPEC.md with many milestones could make one file large; not addressed here, not evidence of a real problem yet |
| B. Give CHECKPOINT.md the same single-location/overwrite rule SPEC.md has | Symmetric with the already-established SPEC.md rule; keeps the richer per-block field format available | Doesn't fix the priority-override bug — a correctly-managed CHECKPOINT.md can still silently out-rank a SPEC.md's own inline content if the two drift, even briefly, out of sync | Rejected: manages a symptom (orphaning) while leaving the actual defect (silent override) in place |
| C. Keep both patterns, reverse priority (inline_spec wins over checkpoint) | Preserves CHECKPOINT.md as an option for specs that want it | Two patterns to keep mentally distinct going forward, for a project of one active SPEC.md at a time; doesn't remove the orphaning risk, only its worst consequence | Rejected: keeps complexity two-pattern-discovery logic requires, for a benefit (an unused richer field format) nothing in this project currently exercises |

A.

B — rejected because it fixes orphaning but not the silent-override
defect that actually caused two commits' worth of validation to
silently target the wrong file. C — rejected because it keeps a second
pattern's discovery-logic complexity for a richer field format nothing
in this project currently uses in practice.

## Consequences

- `docs/BACKLOG.md`'s "CHECKPOINT.md orphaning recurs" entry is now
  resolved by this ADR — its own text explicitly left the decision open
  pending this outcome.
- `scripts/verify.py`'s module docstring, `classify()`, and its
  `validate_structure()` dispatch no longer reference CHECKPOINT.md; the
  now-dead `validate_checkpoint_structure()` function and its two
  regex constants were removed in the same commit, not left as unused
  code.
- Any future component wanting per-milestone `verify:`/`done-when:`/
  `status:` structure keeps that inline, within its SPEC.md's own
  Milestones section (as this consolidated SPEC.md already does),
  rather than in a separate paired file.

## Confirmation & Revisit

TDD, per `docs/CONSTITUTION.md`'s TDD rule (a discovery mechanism whose
entire job is choosing the right pattern under specific conditions):
`classify()` tested in isolation against a scratch fixture with both a
well-formed inline-Milestones SPEC.md and a CHECKPOINT.md present —
confirmed RED (pre-fix: returns `"checkpoint"`, silently ignoring the
well-formed inline content) and GREEN (post-fix: returns `"inline_spec"`
even with CHECKPOINT.md still present). Re-ran `scripts/verify.py`
against the real repo after deleting root `CHECKPOINT.md`: confirms
`pattern: "inline_spec"`, `source_file` is this SPEC.md itself,
structurally OK.

If a future need for CHECKPOINT.md's richer per-block field format
becomes concrete (not hypothetical), revisit this ADR rather than
silently reintroducing a paired-file pattern without deciding how to
avoid the priority-override defect this ADR removed.

**Source.** DocOps SPEC.md M6 (2026-08-20), resolving `docs/BACKLOG.md`'s
"CHECKPOINT.md orphaning recurs" entry (2026-08-20), which itself traced
back to the `dcb84e4` DocOps SPEC.md finding.
