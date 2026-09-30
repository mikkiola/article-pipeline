# Current Mission

## GOAL
ID: G052, G055
Title: Turn real work into content; separate fact from interpretation
Source: ../SYSTEM_GOALS.md
Goals version: 2026-09-30.v1
Reference: docs/PROJECT.md

## NOW
Rebuilding `daily_linkedin_author.py`'s fact-mode prompt/response pipeline to match
ADR-0059's five-step evidence-grounded reasoning contract (`docs/BACKLOG.md`'s [B-058]).

## CURRENT STEP
Wire in identity continuity (ADR-0059 Decision point 6): pass the author's real
recent published posts and a persisted `identity_state` into fact-mode generation.

## WHY
The five-step prompt rebuild (B-058's first checkbox) is already committed
(`e582b8c`). Identity continuity is the next unchecked item in [B-058], and no
other checkbox in that entry can start before it per the entry's own ordering.

## DONE WHEN
[B-058]'s four checkboxes are all satisfied — five-step prompt rebuilt (done),
identity continuity wired, `test_daily_linkedin_author.py` extended for the new
structure, and `docs/ARCHITECTURE.md`'s Author row Validation column re-validated
against real generated posts — and [B-058] is closed in `docs/BACKLOG.md`.

## IN SCOPE
- `identity_state`/recent-posts wiring into the fact-mode generation path
- Test coverage extension for the five-step structure and identity wiring
- Re-validating `docs/ARCHITECTURE.md`'s Author row once posts are checked

## OUT OF SCOPE
- `_build_idea_fallback_prompt()` / idea_fallback mode (governed separately by ADR-0044)
- The automation-only-day pre-call guard ([B-069], filed separately)
- [B-068]'s metadata-field schema detail (decision already closed; schema deferred)
- Quality Gate, Platform Adapter, Multi-Source Claim Layer, or any Phase 4/5 work
- General architecture cleanup or refactors not required for [B-058]

## BLOCKERS
- None known.

## STATUS
ACTIVE

## SCOPE RULE
Discovered issues, ideas, opportunities, cleanup, refactors, and future work do not
become part of the current mission unless they are required by DONE WHEN or
explicitly added to IN SCOPE. Otherwise record them in the appropriate
backlog/state mechanism and continue the current mission.
