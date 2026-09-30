# Current Mission

## GOAL
ID: G061, G064
Title: Measure publication quality; improve content based on past results
Source: ../SYSTEM_GOALS.md
Goals version: 2026-09-30.v1
Reference: docs/PROJECT.md

## NOW
Building M3 (Owner Verdict Capture, LinkedIn) per `SPEC.md`'s milestone
definition: an append-only, `content_id`-keyed verdict event stream,
independent of publication lifecycle state.

## CURRENT STEP
Design and implement the verdict record schema and storage mechanism
(`verdict/output/`, JSON records) per SPEC.md requirements 14-16 and
ADR-0050 points 1-2.

## WHY
M3 is a named, explicit dependency of `SAFETY_PAUSE`'s trigger and
proactive credential alerting (ADR-0054), both currently unbuilt and
blocking full M2 safety coverage. M3 is also SPEC.md's own next
not-started milestone in the Publication Core Loop sequence.

## DONE WHEN
SPEC.md's M3 checkbox is satisfied: both a `recorded` and a `missing`
`verdict_status` are demonstrated (a verdict recorded for a real M2
publication, and a Weekly snapshot showing no verdict yet for another)
— and M3's own `status:` line in SPEC.md is updated from `not started`
to reflect this.

## IN SCOPE
- Verdict event stream schema and writer (`verdict/output/`, JSON,
  `content_id`-keyed)
- Recording a `verdict_type` (`good`/`trash`/`style-off`) with
  `received_at` and optional comment
- Demonstrating both `recorded` and `missing` `verdict_status` outcomes
- No Telegram delivery mechanism (M5, blocked on `[B-065]`) — verdicts
  may be recorded via a direct, manual/test-only interface for this
  milestone; a real Telegram round-trip is explicitly M5's own scope,
  not M3's

## OUT OF SCOPE
- M5 (Telegram HITL Bot) and any Telegram transport
- M6 (Weekly Snapshot & Pattern Detection) beyond the single
  demonstration snapshot DONE WHEN requires
- `SAFETY_PAUSE`'s actual trigger wiring (depends on M3 being done, but
  wiring the trigger itself is separate, later work)
- M4 (Habr Manual Outbox)
- B-069 (automation-only-day pre-call guard)
- Any Quality Gate, Platform Adapter, or Multi-Source Claim Layer work

## BLOCKERS
- None known.

## PREVIOUS MISSION COMPLETION (B-058, historical — superseded by this mission)
DONE WHEN is satisfied: all four of [B-058]'s checkboxes are checked and the
entry is closed in `docs/BACKLOG.md` (commit `5ab85f9`, `Closes: B-058`).
This says nothing about whether the referenced goals (G052/G055) are
themselves achieved — that remains an owner decision, not implied by this
mission's completion, per the Mission Harness section's own
Mission-Done-≠-Goal-Achieved rule.

## STATUS
ACTIVE

## SCOPE RULE
Discovered issues, ideas, opportunities, cleanup, refactors, and future work do not
become part of the current mission unless they are required by DONE WHEN or
explicitly added to IN SCOPE. Otherwise record them in the appropriate
backlog/state mechanism and continue the current mission.
