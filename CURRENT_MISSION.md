# Current Mission

## GOAL
ID: G057
Title: see SYSTEM_GOALS.md, G057
Source: ../SYSTEM_GOALS.md
Goals version: 2026-09-30.v1
Reference: docs/PROJECT.md

## NOW
Restore the daily LinkedIn auto-publish after the two identified failure
causes.

## CURRENT STEP
Parser fix committed locally (`fdf308d`) and not pushed. It awaits the
owner's push approval and the next scheduled run.

## WHY
No post for 2026-10-01 (the model response was not parseable) or 2026-10-02
(the consumer at `aa14bb9` expected schema 2 while Collector emitted 3, so
the bootstrap gate blocked the day). The schema mismatch is resolved on
`origin/main` as of `880551c`. The remaining cause is the parser.

## DONE WHEN
The first scheduled run after the fixes either publishes a real post, or
skips correctly. The result must be confirmed by literal workflow logs and
the Registry record.

## IN SCOPE
- The failure to parse the model response
- Verify version alignment holds. No new rollout mechanism, per ADR-0056
  order independence.

## OUT OF SCOPE
- M4 in full, including its research session
- M5 through M8
- B-069 and B-070
- The `identity_state` writer
- Changing the model used by `call_model`
- A Registry record for the automation-only-day outcome
- The misleading block reason in the Registry record, because fixing the
  contract does not require it
- SPEC.md drift
- Any push other than one the owner approves explicitly

## BLOCKERS
- None known.

## PREVIOUS MISSION COMPLETION (B-058, historical — superseded by this mission)
DONE WHEN is satisfied: all four of [B-058]'s checkboxes are checked and the
entry is closed in `docs/BACKLOG.md` (commit `5ab85f9`, `Closes: B-058`).
This says nothing about whether the referenced goals (G052/G055) are
themselves achieved — that remains an owner decision, not implied by this
mission's completion, per the Mission Harness section's own
Mission-Done-≠-Goal-Achieved rule.

## PREVIOUS MISSION COMPLETION (M3, historical — superseded by this mission)
DONE WHEN is satisfied: SPEC.md's M3 checkbox is checked (`[x]`) and its
`status:` line reads `done`, per commits `07aec0e` (verdict/ package,
15/15 tests, real demonstration against real M2-published `content_id`s
`linkedin-2026-09-29`/`linkedin-2026-09-28`) and `23c216b`
(docs/ARCHITECTURE.md's Owner Verdict Capture row). This says nothing
about whether the referenced goals (G061/G064) are themselves achieved
— that remains an owner decision, not implied by this mission's
completion, per the Mission Harness section's own
Mission-Done-≠-Goal-Achieved rule.

## STATUS
ACTIVE

## SCOPE RULE
Discovered issues, ideas, opportunities, cleanup, refactors, and future work do not
become part of the current mission unless they are required by DONE WHEN or
explicitly added to IN SCOPE. Otherwise record them in the appropriate
backlog/state mechanism and continue the current mission.
