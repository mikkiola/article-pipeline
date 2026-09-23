---
id: ADR-0052
status: Accepted
supersedes: ADR-0050
superseded_by: null
source_type: verbatim
---

# ADR-0052: Pattern-detection thresholds start unset (OBSERVE_ONLY), not a placeholder number

## Status

Accepted.

## Context & Constraints

ADR-0050 established the verdict/weekly/prompt-change feedback loop: async
verdict events, snapshot-based Weekly runs, version-targeted Change Proposals
with optimistic concurrency, and manual Habr edits captured as Evidence. Its
Confirmation & Revisit section named `N=7` as the number of eligible
publications to watch when judging whether a prompt fix "worked," explicitly
calling it "an arbitrary starting value, not based on data or prior art" but
still treating it as a live, functioning number in the meantime, with a
caveat attached.

During the Publication Core Loop `/spec` interview (2026-09-23), designing
Weekly's "recurring pattern" detection (ADR-0050 point 4 — the mechanism that
turns repeated Evidence of the same kind into a Change Proposal) surfaced the
same problem in a second place: how many occurrences count as "recurring"
before Weekly acts. The owner identified that treating either number as "a
live default, sorry it's a guess" is inconsistent with the actual epistemic
state: there is no evidence yet that any specific number is better than any
other, and a number that changes system behavior (triggering an automatic
Change Proposal, or declaring a prompt fix confirmed) is owner policy, not
something architecture should default silently.

This does not change ADR-0050's points 1, 2, 3, or 4 (verdict as an
asynchronous event; snapshot-based Weekly runs with `verdict_status`;
version-targeted Change Proposals with optimistic concurrency and `STALE`
handling; manual Habr edits as Evidence) — all remain exactly as ADR-0050
stated them. This ADR narrows to one thing: how an unset numeric threshold is
represented and behaves before the owner sets it, replacing "a live
placeholder number with a caveat" in two places (the recurring-pattern count,
and `N=7`'s monitoring window) with an explicit unset/inactive state.

## Decision

A detected repetition is represented as a `PatternCandidate` object —
`pattern_signature`, `occurrence_count`, `first_seen_at`, `last_seen_at`,
`activity_window_ids[]`, `evidence[]` — that Weekly always populates and
accumulates, regardless of whether any threshold is set. It additionally
carries `threshold_status: uncalibrated | calibrated`, `threshold: null |
<int>`, and `action_policy: disabled | enabled`.

While `action_policy = disabled` (the starting state, `OBSERVE_ONLY`), Weekly
surfaces pattern candidates and their growing `occurrence_count` but drafts
no Change Proposal automatically, no matter how high the count climbs. Once
the owner sets an explicit `threshold` value (an owner action, not a code
default), `action_policy` flips to `enabled`, and Weekly starts drafting
Change Proposals for candidates whose `occurrence_count` crosses that
threshold.

The same treatment applies retroactively to `N` in "fewer recurrences over
the next `N` eligible publications" (ADR-0050's prompt-fix-confirmation
window): it starts `null`/`OBSERVE_ONLY` — Weekly still records and reports
recurrence counts after a prompt version change, but does not claim a fix is
"confirmed" or "not confirmed" against any number until the owner sets one.
ADR-0050's own text treated `N=7` as a functioning value with a caveat
attached; this was an inconsistency this ADR corrects, not a new position
introduced from nothing.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| **A. Keep ADR-0050's original framing** (a live default number, e.g. `N=7` or a recurrence count of 3, used until "real data suggests a better one") | Rejected. A number silently in effect, with a footnote saying it's a guess, still drives real behavior (an automatic Change Proposal, a fix-confirmed claim) — the caveat doesn't stop the number from acting as policy nobody actually chose. |
| **B. Chosen — thresholds start unset/`OBSERVE_ONLY`; the system observes and reports, takes no threshold-gated action, until the owner explicitly sets a value** | The system is fully capable of describing what it sees (`PatternCandidate`, recurrence counts, per-prompt-version recurrence after a fix) from day one — nothing about detection or reporting waits on a threshold. Only the automatic *action* (drafting a proposal, declaring a fix confirmed) waits for an owner-supplied number, which is the correct owner/architecture boundary line. |

## Consequences

- `weekly/`'s data model (Publication Core Loop `/spec`, M6/M7) must include
  `PatternCandidate` with the fields listed above; a Weekly implementation
  that infers a hardcoded threshold instead does not satisfy this decision.
- Change Proposals cannot be drafted automatically until the owner has
  explicitly set at least one threshold — the system has no default
  "reasonable" count to fall back on, by design.
- The prompt-fix-confirmation window (post-ADR-0050's `N`) is likewise
  unset by default; Weekly reports recurrence counts per prompt version but
  does not itself assert "the fix worked" until the owner sets a window.
- ADR-0050's own frontmatter is updated (`status: Superseded`,
  `superseded_by: ADR-0052`) per this project's Supersedes/Superseded-by
  convention (ADR-0036/ADR-0040) — its points 1-4 remain the operative
  design, narrowed only as described above, not replaced wholesale.

## Confirmation & Revisit

Confirmed when the first `PatternCandidate` accumulates a real
`occurrence_count` from actual recurring Evidence with `action_policy:
disabled`, and no Change Proposal is drafted from it until the owner sets a
threshold — proving the OBSERVE_ONLY default doesn't silently act.

Revisit once the owner sets real threshold values from actual operating
data — at that point `threshold_status` moves to `calibrated` and
`action_policy` to `enabled`; this is the intended, expected outcome of this
decision working, not a case requiring a new ADR by itself. A new ADR would
be needed only if the owner later wants the system to propose a starting
threshold on its own (reintroducing exactly the pattern this ADR rejects).

**Source.** Owner decision, 2026-09-23, during the Publication Core Loop
`/spec` interview — identified as a direct inconsistency in ADR-0050's
already-accepted `N=7` framing, corrected in the same terms across both the
recurring-pattern threshold and `N=7` itself.
