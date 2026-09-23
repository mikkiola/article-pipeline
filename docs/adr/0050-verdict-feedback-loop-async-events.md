---
id: ADR-0050
status: Superseded
supersedes: null
superseded_by: ADR-0052
source_type: inferred
---

# ADR-0050: Verdict feedback loop as async events, not publication lifecycle

## Status

Superseded by ADR-0052 — narrowly, on one point only: the `N=7`
prompt-fix-monitoring window named in this ADR's own Confirmation & Revisit
section below was treated as a live default value with a caveat attached;
ADR-0052 corrects this to start unset (`OBSERVE_ONLY`) instead, the same
treatment given to Weekly's recurring-pattern threshold. Points 1-4 of this
ADR's Decision section remain the operative design, unchanged.

## Context & Constraints

The Publication Core Loop (ROADMAP, committed phase order, row 1) includes a
feedback loop after publication: for LinkedIn, the owner gives a verdict
(`good` / `trash` / `style-off`) on a published piece; for Habr, the owner
manually edits the AI-generated draft before publishing it herself, since Habr
has no confirmed automatic publication route (ROADMAP's open questions). A
weekly job aggregates this feedback across publications, detects recurring
patterns, and proposes changes to the Author prompt. The owner approves or
rejects each proposal before any prompt change takes effect.

Review of this design in the architect chat found three gaps, each with a
shared incorrect premise: that a verdict must be a required, timed lifecycle
stage of a publication, blocking or gating that publication's own completion.
This premise fails on inspection — a verdict can be given late, never, or not
at all for a given piece, and a publication that never receives a verdict is
still a real, completed publication, not a stuck one.

This ADR does not choose Platform Adapter's or Quality Gate's design (both Not
started, ARCHITECTURE.md) — it fixes the shape of the verdict/weekly/prompt-
change subsystem those components will eventually feed into.

## Decision

Four connected points, one design for one subsystem:

1. **Verdict is an asynchronous feedback event, not a publication lifecycle
   stage.** A publication's state machine does not include an
   `AWAITING_VERDICT` state with a timeout. Verdict and Publication are two
   independent, append-only streams joined by `content_id`. A verdict may
   arrive before, during, or after any Weekly run; it never expires and is
   never required to "complete" a publication's lifecycle.

2. **Weekly runs are immutable, timestamped snapshots, not a queue that waits
   for verdicts.** Each Weekly run takes a snapshot of all eligible
   publications as of that run's time, and for each one records
   `verdict_status: recorded | missing` — never silently skipping unverdicted
   items. A snapshot is never overwritten; a later verdict becomes visible to
   the next Weekly snapshot, not a rewrite of a past one.

3. **A Change Proposal targets a specific Author prompt version and uses
   optimistic concurrency, not a lock or queue.** Every Change Proposal
   records `target_prompt_version`. At approval time, if
   `target_prompt_version` still equals the current live prompt version, the
   proposal applies and creates a new version. If the live version has
   already moved (another proposal was approved first), the proposal becomes
   `STALE` and must not be applied automatically. This allows multiple
   proposals to be drafted concurrently while guaranteeing only one prompt
   version is ever "under monitoring" at a time, without needing a proposal
   queue or priority mechanism.

4. **Manual Habr edits are Evidence, not a direct prompt change.** When the
   owner manually edits an AI-generated Habr draft before publishing, the diff
   between the draft and the published text is captured as an Evidence
   record — the same kind of signal a `trash` or `style-off` verdict produces.
   A single edit changes nothing on its own. Weekly aggregates repeated
   Evidence of the same kind across multiple articles; only a recurring
   pattern produces a Change Proposal, which still requires owner approval
   before any Author prompt version changes. This preserves the existing rule
   that prompt changes are never inferred silently from a single data point,
   while still letting Habr's manual-edit signal feed the same improvement
   loop LinkedIn's verdicts feed.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| **A. Verdict as a required, timed publication lifecycle stage** (`AWAITING_VERDICT` with a timeout) | Rejected — the shared incorrect premise both external cross-checks converged on rejecting. Forces an arbitrary timeout on a human action with no natural deadline, and makes a publication's own completion depend on the owner's later, optional behavior. |
| **B. Weekly as a queue that waits for all pending verdicts before running** | Rejected. Couples the weekly cadence to verdict arrival, defeating the purpose of a fixed-cadence report; also reintroduces the timeout problem from Option A one level up. |
| **C. Change Proposals serialized through a queue or lock on the live prompt** | Rejected. A queue or lock requires deciding proposal priority/ordering when several are drafted concurrently — a mechanism this project doesn't need, since optimistic concurrency (point 3) gets the same single-live-version guarantee without it. |
| **D. Manual Habr edits treated as an immediate, direct prompt change** | Rejected. Violates the existing rule that prompt changes are never inferred from a single data point; a single edit is often stylistic noise, not a pattern. |
| **Chosen — points 1-4 above** | Append-only, snapshot-based, version-targeted, evidence-first design. Each point removes one required synchronization point (a lifecycle timeout, a queue wait, a lock, a single-edit inference) in favor of an async, eventually-aggregated signal. |

## Consequences

- Publication's own state machine (once Platform Adapter is designed) does
  not need an `AWAITING_VERDICT` state or a verdict timeout field.
- Weekly run records must carry `verdict_status: recorded | missing` per
  publication in the snapshot — a Weekly implementation that silently omits
  unverdicted publications does not satisfy this decision.
- Change Proposal records must carry `target_prompt_version` and a `STALE`
  outcome path; an approval flow that applies a proposal without checking the
  live prompt version against `target_prompt_version` does not satisfy this
  decision.
- Habr's manual-edit capture (diff between draft and published text) becomes
  a new Evidence-producing path, parallel to LinkedIn's verdict path, feeding
  the same Weekly aggregation — this is new scope for whatever component
  captures Habr's published text, not yet assigned to a named component.
- Quality Gate, Platform Adapter, and Weekly's own implementation (all Not
  started) inherit this shape as a constraint when their `/spec` interviews
  happen.

## Confirmation & Revisit

**Known, accepted limitation.** Judging whether a prompt fix "worked" (fewer
recurrences of the targeted pattern over the next `N=7` eligible publications
produced by the new prompt version) is an association, not a proven causal
effect. There is no control group, so a drop in the pattern's frequency after
a prompt version change is evidence consistent with the fix working, not
proof that the fix caused the drop. `N=7` is an arbitrary starting value, not
based on data or prior art, and is expected to be revised once real operating
data suggests a better number.

This decision is confirmed when the first Weekly run produces a snapshot with
at least one `verdict_status: missing` publication (proving the async design
doesn't stall on a missing verdict) and when the first Change Proposal
approval correctly applies or goes `STALE` depending on `target_prompt_version`
against the live version at approval time.

Revisit if operating data shows `N=7` is clearly wrong in either direction
(too short to detect real change, too long to stay useful), or if a future
need arises to treat verdict as a hard publication gate after all (e.g. a
platform-side requirement this ADR did not anticipate) — via a new,
superseding ADR, not an edit to this one.

**Source.** Developed in the architect chat (Cowork), incorporating two
independent external AI cross-checks that both converged on rejecting a
shared incorrect premise — that verdict must be a required, timed lifecycle
stage of a publication — and arrived at compatible solutions: append-only
verdict events, snapshot-based Weekly runs, and version-targeted proposals
with staleness checks. Recorded by Claude Code, 2026-09-23, per the owner's
task to record (not re-derive or re-evaluate) this already-made decision.
