# Current Mission

## GOAL
ID: G057
Title: see SYSTEM_GOALS.md, G057
Source: ../SYSTEM_GOALS.md
Goals version: 2026-09-30.v1
Reference: docs/PROJECT.md

## NOW
Make every run of linkedin_publisher/daily_publish.py resolve to exactly one
named outcome with a fixed exit code, and expose that outcome in the scheduled
workflow, instead of relying on bare process exit and "no files to commit".

## CURRENT STEP
Code, tests, SPEC.md FR41 and ADR-0067 are in `dbd9027` on `main` (2026-10-16);
this status text is in the docs commit that follows it. The runtime workflow
change was pushed to the runtime repository before the code push, as required.
Awaiting the first scheduled run after rollout to confirm the outcome in its
literal log or job summary; [B-072] stays open.

## WHY
The previous G057 mission restored publishing and logged [B-072] and [B-073]
as residual risks, not fixed. Gate-blocked days and automation-only days end
`success` with no trace beyond the run log (scheduled runs 2026-10-11 to
2026-10-14 are four such days), and a schema-incompatible brief on 2026-10-02
produced a green run with a generic block reason.
The diagnostic of a failed integrity check is kept only in the run log and,
once the runtime workflow exposes them, the job summary and the outcome file,
within the GitHub Actions retention of the repository; it is not a durable
archive.

## DONE WHEN
- daily_publish.py resolves each run to one of PUBLISHED,
  SKIPPED_NO_ELIGIBLE_CONTENT, SKIPPED_SAFETY_PAUSE,
  SKIPPED_ALREADY_PUBLISHED, SKIPPED_AUTOMATION_ONLY (exit 0) or
  FAILED_INTEGRITY, FAILED (exit 1), each proven by a named test.
- FAILED_INTEGRITY fires only on a gate block caused by a confirmed integrity
  violation; existing per-unit exclusion with valid-unit continuation is
  unchanged.
- A schema-incompatible brief yields FAILED_INTEGRITY carrying the specific
  "schema_version=<n>, expected <m>" diagnostic, with no model call, no
  publish and no block PublicationRecord.
- A persistence failure after a confirmed publish fails the job, preserves the
  returned URL, and makes exactly one publish call.
- The runtime workflow exposes the outcome and persists Registry and state
  files on a failed run, confirmed by the literal log or job summary of the
  first scheduled run after rollout. The FAILED_INTEGRITY diagnostic there is
  retained only within the repository's GitHub Actions retention.
- The SPEC.md run-outcome requirement, the ADR and the BACKLOG status note
  listed in the plan are in place.

## IN SCOPE
- linkedin_publisher/daily_publish.py and its tests
- the runtime repository's scheduled workflow (separate repository, separate
  change)
- SPEC.md run-outcome requirement and FR9 clarification, one ADR, a status
  note under [B-072]
- Owner-directed 2026-10-16 and 2026-10-20, under [B-071] (SPEC.md M9):
  simplifying the Habr draft fragment-admission rule to an author check, and
  the Habr draft track that carries it: `habr_draft/` code and tests, ADR-0068
  to ADR-0071, SPEC.md M9 (requirements 42-57), the regenerated ADR index, and
  the two items filed as [B-077] and [B-078]. The owner committed and pushed
  the track to `main` on 2026-10-20 (`c2314b3`, `a098689`, `2bd02c4`,
  `48b2712`), including `author/daily_linkedin_author.py` (`call_model`
  keyword-only parameters for the Habr path; LinkedIn defaults unchanged;
  their tests are in `3432cfa`) and ADR-0068 (the Q rubric decision). A
  one-time exception to the Habr line below; further Habr Draft Automation
  work stays out of scope.

## OUT OF SCOPE
- [B-073] (stays a separate backlog item) and [B-069]
- [B-076]'s record type, any new Registry record, any new gate_status value
- the PublicationRecord schema, writer semantics, pre_filter, the Collector
  adapter
- Collector repository changes, including a cross-repository schema-constant
  check
- retries, a write-ahead intent record, new channels, observability redesign
- the Habr Draft Automation track, except the work listed under IN SCOPE
- closing [B-072] on the strength of this mission alone
- Any push other than one the owner approves explicitly

## BLOCKERS
- Not yet confirmed by a scheduled run: DONE WHEN's workflow criterion needs the
  literal log or job summary of the first scheduled run after rollout.
- Rollout order (followed on 2026-10-16: runtime workflow first, then the code):
  the runtime workflow change goes out before or together with the code, never
  after; without it, local Registry and state writes made before a failed run
  are dropped silently.

## PREVIOUS MISSION COMPLETION (G057 restore of the daily LinkedIn auto-publish, historical — superseded by this mission)
DONE WHEN was satisfied by the first scheduled run after the fixes:
- Workflow run `37088686351` (`linkedin-daily-publish.yml`, event `schedule`,
  `headSha` `1d51f76`, created 2026-10-03T02:07:30Z) concluded `success`. Its
  publish-step log contains
  `Published: https://www.linkedin.com/feed/update/urn:li:share:7511970282216210432/`.
- Registry record `linkedin-2026-10-03` on `registry-data` has
  `gate_status: pass` and `block_reason: null`.
- Post visibility on LinkedIn: confirmed visible by the Owner on 2026-10-06; not independently checked by Claude. The
  closure rests on the run log and the Registry record above, which already
  satisfy DONE WHEN.

The next three scheduled runs (`37172049384` for 2026-10-04, `37254188010` for
2026-10-05, `37407583220` for 2026-10-06; all on `1d51f76`) each logged
`Automation-only day detected (selected_cluster='radar-vault')` and published
nothing. Checked against commit authorship, those skips were correct: the only
commits in those windows were `github-actions[bot]` Collector data commits,
`Radar Bot` commits, and one `vault backup:` commit that touched only
`.obsidian/graph.json`; no manual engineering commit existed in any tracked
repository. Caveat for 2026-10-06: the only non-bot commit in the window was an
automatic vault-backup commit under the Owner's name, touching only
`.obsidian/graph.json`. The model classified the day correctly but could not see
authors or file names, only commit subjects, stated Why/Effect lines and counts.
The model's own stated
reasoning for those days was not persisted and was not reviewed.

Residual risks found while closing, recorded as `[B-072]` and `[B-073]` in
`docs/BACKLOG.md` with per-claim evidence status, not fixed there.

This says nothing about whether the referenced goal (G057) is itself achieved
— that remains an owner decision, not implied by this mission's completion,
per the Mission Harness section's own Mission-Done-≠-Goal-Achieved rule.
`SYSTEM_GOALS.md` is not modified.

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
