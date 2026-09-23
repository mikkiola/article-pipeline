# Publication Core Loop — Specification

## Overview

Original problem statement (quoted verbatim, Step 3.5 check): "Run `/spec`
for the full Publication Core Loop: LinkedIn auto-publish, Habr manual
outbox, the new Telegram HITL bot, the weekly verdict/report mechanism
(including the four points recorded in the ADR above), and Quality Gate —
as one interview with an internal milestone structure (M1..Mn), not several
fragmented specs."

Builds the first end-to-end, zero-manual-step publication loop
(`docs/PROJECT.md`'s Definition of Done): LinkedIn publishes automatically
first (ADR-0049), Habr stays a manual-outbox hand-off (no confirmed
automatic Habr route exists), a Telegram bot is the owner's only manual
touchpoint (Owner Verdicts, Change Proposal approval, Weekly reports,
alerts — never gating a publish decision), and a weekly job turns
accumulated feedback into monitored, owner-approved Author prompt changes
(ADR-0050, ADR-0052).

**Glossary (resolves a real naming collision found in this repo's `/spec`
pre-spec check):**
- **Owner Verdict** — the owner's post-publication feedback
  (`good`/`trash`/`style-off`), an async event per ADR-0050 point 1. This
  spec always uses this full term, never bare "verdict."
- **Strategy Verdict** — the pre-existing, unrelated concept:
  Strategy Layer's own output artifact (`strategy_layer/output/verdict_*.json`,
  consumed by Author via `AuthoringContext`). Untouched by this spec.

## Goals

- [ ] M1 — Publication Registry exists; every publication event is
      recorded with platform, URL, publication time, and gate metadata.
- [ ] M2 — LinkedIn publishes at least one real post fully automatically
      (no manual step), gated by a named bootstrap gate.
- [ ] M3 — Owner Verdict capture exists for LinkedIn as an async,
      never-expiring event stream.
- [ ] M4 — Habr's draft reaches the owner via Telegram; her final edited
      text is captured as Evidence via her existing per-article Google
      Docs folder convention.
- [ ] M5 — A Telegram HITL bot delivers Owner Verdict prompts, Change
      Proposal approvals, Weekly reports, and alerts, in Russian.
- [ ] M6 — Weekly takes immutable snapshots, tracks `verdict_status`, and
      detects recurring patterns in `OBSERVE_ONLY` mode (ADR-0052).
- [ ] M7 — Change Proposals are version-targeted with optimistic
      concurrency; approved proposals apply, stale ones are discarded.
- [ ] M8 — Quality Gate enforces the full formal R6 rule, replacing M2's
      bootstrap gate for new publications, without retroactively
      reclassifying M2-M7's history.

## Tech Stack

No new language/runtime: Python, matching every existing component
(`author/`, `strategy_layer/`, `evidence_package/`). New external
integrations, each net-new to this repo's own code (verified by direct
grep — none exist here today):

- **LinkedIn API** — `w_member_social` scope, Share on LinkedIn product
  (self-serve, no partner review per ADR-0049's research).
- **Telegram Bot API** — `sendMessage` + cron-polling `getUpdates`,
  consumed from ToolTempest's shared transport once ADR-0051/`[B-065]`
  lands (named dependency of M5, not built in this spec).
- **Google Drive/Docs API** — new service-account credential and client,
  scoped to the owner's existing per-Habr-article Drive folders. This is
  new code in this repo; the owner's existing Drive access is a
  Cowork/architect-chat-layer capability today, not article-pipeline code
  (confirmed directly with the owner during this interview).
- **GitHub Actions** — scheduling for LinkedIn's daily run, Habr's
  outbox check, and Weekly's cadence, matching Collector's existing
  `daily.yml`/`weekly.yml` cron pattern.

## Detailed Requirements

### Functional Requirements — M1: Publication Registry

1. One JSON record per publication event, under
   `publication_registry/output/`, git-committed (Immutable Lineage,
   matching every existing component's convention).
2. Parent entity is the published piece itself, **not** the underlying
   Claim — the same Claim could in principle be published more than once.
3. `content_id` is the Registry's own minted primary key — the join key
   Owner Verdict, Weekly, and Change Proposal streams all use, per
   ADR-0050. It is **not** `claim_id`.
4. Each record carries at minimum: `content_id`, `platform`
   (`linkedin`/`habr`), `url`, `published_at`, `claim_id` (link back to
   the source Claim), and the gate metadata below.
5. Gate metadata, persisted per publication so history never loses which
   gate a piece was actually evaluated under:
   - `gate_policy`: `bootstrap` (M2-M7) or `R6` (M8+).
   - `gate_version`.
   - `gate_status`: `pass` / `block`.
   - `block_reason` (present only when `gate_status = block`).
   - `gate_evaluated_at`.
6. M8's activation of the real R6 gate does **not** retroactively
   reclassify M2-M7 publications — their recorded `gate_policy =
   bootstrap` and its `gate_status` remain valid history for the
   milestone that produced them.

### Functional Requirements — M2: LinkedIn Auto-Publish (bootstrap-gated)

7. A scheduled (daily, matching `daily_linkedin_author.py`'s existing
   cadence) job generates a candidate LinkedIn post, evaluates it through
   the **bootstrap gate**, and — on pass — publishes it via the LinkedIn
   API with no manual step, then writes the Publication Registry record.
8. **Bootstrap gate = the existing, already-implemented Strategy Layer
   mechanism** — `strategy_layer/pre_filter.py`'s `classify_unit()` (the
   two-dimension `integrity_status`/`corroboration_status` matrix,
   ADR-0047) and `check_all_claims_unverifiable_gate()` (run-level
   `status="gated"` when nothing survives). Confirmed by direct read
   during this interview: this mechanism exists today, is already
   139/137-tested, and covers exactly the bootstrap-gate responsibility
   (block on invalid integrity or disputed/unsubstantiated/pending
   corroboration). **This is explicitly weaker than R6** — it has no
   `activity_anchor`, no per-predicate `proves_predicate` verifier, and
   no `scope: external` distinction — and must never be presented to the
   owner or in any report as R6. `gate_policy = bootstrap` on every
   record it produces makes this structurally unambiguous.
9. Bootstrap-gate block → no publish; a structured record still writes
   to the Registry (`gate_status = block`, `block_reason` from
   `pre_filter`'s own `_EXCLUDE_REASON`).
10. **Circuit breaker — `SAFETY_PAUSE`.** One explicit `trash` Owner
    Verdict on an already-published LinkedIn post opens the circuit:
    future scheduled auto-publish runs are skipped while `SAFETY_PAUSE`
    is active. This is a deterministic, evidence-based trigger — no
    invented consecutive-failure count. `SAFETY_PAUSE` is a state
    separate from an ordinary bootstrap/R6 `block` — a normal "no
    eligible content today" block must never open the circuit.
11. Recovery from `SAFETY_PAUSE` is manual: the owner explicitly lifts it
    via Telegram once she's addressed the cause. She never generates or
    publishes content herself — lifting the pause is her only action,
    consistent with "no manual step" for the pipeline's own output.
12. Known, accepted limitation (not a new open question): the delay
    between a bad publish and the resulting `SAFETY_PAUSE` depends
    entirely on how quickly the owner responds with a `trash` verdict in
    Telegram, since Owner Verdict has no timeout (ADR-0050 point 1).
13. LinkedIn token renewal: a scheduled check tracks the token's known
    ~60-day expiry (ADR-0049) and sends a Telegram alert before it
    expires; renewal itself is manual re-auth by the owner. No
    refresh-token flow is built (not confirmed to exist for the
    Share-on-LinkedIn product).

### Functional Requirements — M3: Owner Verdict (LinkedIn)

14. Owner Verdict is an append-only event stream (ADR-0050 point 1),
    stored as JSON records under `verdict/output/`, one record per
    verdict, keyed by `content_id` (never `claim_id`).
15. A verdict record: `content_id`, `verdict_type`
    (`good`/`trash`/`style-off`), `received_at`, optional free-text
    comment (owner may add context in her Telegram reply).
16. No publication's lifecycle state depends on a verdict arriving. A
    publication with no verdict is a complete, valid Registry record —
    `verdict_status` is a Weekly-snapshot concept (M6), not a
    Registry/publication field.

### Functional Requirements — M4: Habr Manual Outbox + Edit Capture

17. Once Author generates a Habr draft, the pipeline sends it to the
    owner via Telegram (draft text or a link to it) — no automatic Habr
    posting exists or is attempted.
18. Edit capture reuses the owner's **existing** per-Habr-article Google
    Docs folder convention (confirmed net-new code for article-pipeline
    itself, not net-new to the owner's workflow): each folder contains
    `YYYY-MM-DD-draft` (Author's generated draft) and `YYYY-MM-DD-final`
    (the owner's own edited, actually-published text). ISO date order,
    not day-first, so filenames sort correctly across month/year
    boundaries.
19. A scheduled job watches for a new `-final` file, diffs it against the
    matching `-draft` file in the same folder, and writes the diff as an
    Evidence record (ADR-0050 point 4) — the same signal kind a `trash`/
    `style-off` verdict produces, feeding the same Weekly aggregation.
20. No Telegram round-trip and no Habr page scraping for this step —
    scraping was explicitly rejected (no confirmed ToS permission, adds
    an HTML-parsing dependency this build otherwise has no need for).
21. New Google Drive API credential/client is real, net-new build scope
    for this milestone (not "already there") — verified directly: no
    Drive/Docs integration exists anywhere in this repo's code today.

### Functional Requirements — M5: Telegram HITL Bot

22. Transport (send `sendMessage`, receive cron-polling `getUpdates` with
    persisted offset and chat_id filtering) is consumed from ToolTempest
    once `[B-065]`/ADR-0051 lands — **named dependency, not built here.**
    Business logic (message formatting, reply parsing, approval
    semantics) is article-pipeline's own, per ADR-0051's scope boundary.
23. Bot responsibilities, confirmed exhaustively during this interview —
    it is **never** a pre-publish approval gate:
    - Deliver Owner Verdict prompts after a publication and parse the
      owner's reply into a `verdict_type`.
    - Deliver Change Proposals (M7) for approve/reject.
    - Deliver Weekly reports (M6).
    - Deliver `SYSTEM_FAILURE`/`SAFETY_PAUSE` alerts and recovery
      messages (M8, M2).
24. All owner-facing text from this bot is **Russian**
    (`docs/CONSTITUTION.md`'s new named exception, this session),
    matching `analyzer`'s and `radar`'s existing precedent.

### Functional Requirements — M6: Weekly Snapshot & Pattern Detection

25. Each Weekly run writes one immutable, timestamped snapshot record
    under `weekly/output/` — never overwritten. A later verdict is
    visible to the *next* snapshot, never rewrites a past one
    (ADR-0050 point 2).
26. Every eligible publication (published since the prior Weekly run's
    cutoff — this project's usual JSON-file weekly-window convention,
    matching `analyzer`'s own weekly cycle) appears in the snapshot with
    `verdict_status: recorded | missing` — never silently omitted.
27. Pattern detection produces `PatternCandidate` objects (ADR-0052):
    `pattern_signature`, `occurrence_count`, `first_seen_at`,
    `last_seen_at`, `activity_window_ids[]`, `evidence[]`,
    `threshold_status: uncalibrated | calibrated`, `threshold: null |
    <int>`, `action_policy: disabled | enabled`.
28. Starting state is `OBSERVE_ONLY` (`action_policy: disabled`,
    `threshold: null`) for every new `pattern_signature` — Weekly
    accumulates and reports candidates but drafts no Change Proposal
    automatically until the owner sets a real threshold from real data.
29. The prompt-fix-confirmation window (originally ADR-0050's `N=7`) gets
    the same treatment (ADR-0052): unset by default, reporting recurrence
    counts per prompt version without asserting a fix is "confirmed"
    until the owner sets a window value.
30. Weekly's report content is specific to that cycle's own data
    (publications, verdict_status, active PatternCandidates, any
    STALE-from-last-week proposals, current `SAFETY_PAUSE` state) — not
    a restatement of the project's general strategic goal.

### Functional Requirements — M7: Change Proposal Mechanism

31. Every Change Proposal carries `target_prompt_version` and a
    **separate `prompt_version` track per channel** (LinkedIn vs. Habr —
    confirmed during this interview: they are already different prompts,
    ADR-0044 vs. ADR-0046, and must not share one version counter or one
    STALE-ness check across channels).
32. Approval: if `target_prompt_version` still equals the channel's
    current live version, the proposal applies and creates a new
    version. If the live version already moved, the proposal becomes
    `STALE` and is never applied automatically.
33. **STALE proposals are terminal** — discarded, no retargeting UI. If
    the same pattern still recurs in a later Weekly run (per its
    `PatternCandidate`, once `action_policy: enabled`), that run drafts a
    fresh proposal targeting the then-current live version.
34. A Change Proposal's content — the actual proposed prompt diff — is
    LLM-drafted from the `PatternCandidate`'s accumulated evidence plus
    the current live prompt text, once `action_policy` is `enabled` for
    that pattern. The owner approves or rejects the drafted diff itself
    via Telegram (M5); the LLM never applies a change unilaterally.
35. Manual Habr edits (M4's Evidence records) feed the same
    `PatternCandidate`/Weekly aggregation LinkedIn's Owner Verdicts feed
    — one shared detection mechanism across both signal kinds, per
    ADR-0050 point 4.

### Functional Requirements — M8: Quality Gate (Real R6)

36. Quality Gate replaces the bootstrap gate for **new** publications
    once activated; M2-M7 history keeps its `gate_policy = bootstrap`
    records unchanged (see M1's requirement 6).
37. **Formal R6 rule** (owner-specified verbatim during this interview —
    a publication passes only if it contains ≥1 Claim meeting all five
    jointly, within a defined Verification Run):
    - `evidence.scope = external` — never
      `source_of_record`/`first_party`/`platform`. Internal telemetry
      re-read from the system that produced it never counts, however
      reproducible.
    - `evidence.provenance.independent_of_origin = true` — the source
      establishes the fact from its own authoritative record, not by
      repeating/paraphrasing/deriving from the claim's own origin.
    - `evidence.proves_predicate = true` — the PASS result of the
      specific verification procedure defined for that predicate type,
      never a free LLM judgment call.
    - `Claim.activity_anchor.valid = true` — causally/semantically
      derived from real activity in the DailyBrief's stable
      `activity_window_id`, not merely mentioned in commit text or
      picked later for topical similarity. Reprocessing the same window
      must preserve the same anchor.
    - No qualifying contradictory Evidence for the same predicate was
      found within that same Verification Run. `disputed` wins over one
      qualifying supporting match.
38. New data-model fields this rule requires: `evidence.scope`,
    `evidence.proves_predicate`, `evidence.provenance.independent_of_origin`,
    `Claim.activity_anchor` (keyed to `activity_window_id`). Keep
    `retrieval_source` (e.g. Linkup, a retrieval mechanism) distinct from
    `evidence_source` (the actual authority retrieved, e.g. an npm/OSV
    page) — a search API is never itself the evidence or the verifier.
39. **Named external prerequisite, not built in this spec:** "Path B
    Claim Extraction" — deriving atomic Claims from real git/CI activity
    with a genuine external anchor, separate from the existing DailyBrief
    self-report format. Confirmed absent from `docs/ARCHITECTURE.md`
    today via direct read. Owner decision (this interview): this gets
    its own, separate `/spec` interview — M8 in this spec states it as a
    blocking dependency, the same treatment ADR-0051 gives the Telegram
    transport for M5.
40. Quality Gate's three outcomes (owner-specified verbatim):
    - **`QUALITY_BLOCK`** — R6 fails because no eligible Claim met all
      five conditions this cycle. Expected and safe; no post, no alert,
      recorded and surfaced in Weekly as `blocked_by_quality_gate`.
    - **`SYSTEM_FAILURE`** — Linkup unavailable, a verifier crashed, the
      Claim contract is invalid, Author produced claim IDs absent from
      Evidence Package, or the publisher errored/returned unknown. No
      post; **immediate Telegram alert**, because this is pipeline
      breakage, not "no material today."
    - Alerting is **state-transition-based**, not per-event: `HEALTHY →
      DEGRADED/FAILED` fires one alert; repeated failures while still
      degraded are aggregated silently (no daily repeat spam); `→
      RECOVERED` fires one recovery message.
    - This distinction matters especially early on, while Path B Claim
      Extraction is new: R6 legitimately failing on "no external claim
      found today" must never be conflated with real system breakage.

## UI/UX Specification

No traditional UI. The Telegram bot (M5) is the only owner-facing
surface: Russian text, message-based (no inline buttons assumed —
reply-text parsing, matching `analyzer/scripts/telegram_bot.py`'s
existing pattern), covering Owner Verdict prompts, Change Proposal
approve/reject, Weekly reports, and alerts.

## API Design

- **LinkedIn**: `w_member_social` scope, personal-profile posting via the
  Share on LinkedIn product (ADR-0049). No partner review needed.
- **Telegram Bot API**: `sendMessage`, cron-polling `getUpdates` (no
  webhook, matching this ecosystem's GitHub-Actions-cron pattern) — via
  the shared ToolTempest transport once `[B-065]` lands.
- **Google Drive/Docs API**: read-only access to the owner's existing
  per-Habr-article folders, via a new service-account credential scoped
  to article-pipeline specifically (net-new, per requirement 21).

## Data Model

New JSON-file-backed stores, one directory per component, matching this
project's existing convention (`evidence_package/output/`,
`strategy_layer/output/`) — no database introduced:

| Directory | Written by | Key fields |
|---|---|---|
| `publication_registry/output/` | M2/M4 | `content_id`, `platform`, `url`, `published_at`, `claim_id`, `gate_policy`, `gate_version`, `gate_status`, `block_reason`, `gate_evaluated_at` |
| `verdict/output/` | M3 | `content_id`, `verdict_type`, `received_at`, comment |
| `weekly/output/` | M6 | immutable per-run snapshot; `verdict_status` per publication; `PatternCandidate[]` |
| `change_proposals/output/` | M7 | `target_prompt_version`, per-channel `prompt_version`, proposed diff, `status` (`pending`/`applied`/`STALE`/`rejected`) |

## Security Considerations

- LinkedIn token, Telegram bot token, and the new Google Drive
  service-account key are secrets — stored as GitHub Actions secrets,
  matching Collector's existing CI credential pattern. No credential is
  committed to the repo.
- Telegram `getUpdates` must filter to the owner's configured `chat_id`
  only, silently dropping any other sender — the same protection
  `analyzer/scripts/telegram_bot.py` already implements, since a bot
  token alone gives no per-bot allowlist on Telegram's side.
- Google Drive access is read-only and scoped to the owner's existing
  Habr-article folders — no write/delete capability needed by this
  pipeline.

## Test Plan

Per `docs/CONSTITUTION.md`'s TDD rule, the following are exactly the
"confirmation/gating mechanism whose entire purpose is to trigger under
specific conditions" class this project already learned (the hard way,
per that rule's own note) needs a test written first, not after:

- Quality Gate's three-outcome state machine (`QUALITY_BLOCK` vs.
  `SYSTEM_FAILURE`, and the `HEALTHY→DEGRADED→RECOVERED` transition-only
  alerting) — write the transition tests before the implementation.
- `SAFETY_PAUSE`'s trigger (one `trash` verdict) and its independence
  from ordinary `QUALITY_BLOCK`/bootstrap-block events — a test proving a
  normal block never opens the circuit.
- Change Proposal optimistic concurrency: a test proving a proposal whose
  `target_prompt_version` has moved goes `STALE` and is never applied.
- `PatternCandidate`'s `OBSERVE_ONLY` default: a test proving no Change
  Proposal is drafted while `action_policy: disabled`, regardless of how
  high `occurrence_count` climbs.

Everything else follows this project's existing convention: real-data
validation once each milestone's mechanism is implemented (matching
every existing component's own "tested on real data" bar), not mocked
end-to-end.

## Milestones

### M1: Publication Registry
- [ ] Registry schema + writer, gate-metadata fields included from day one
- verify: real Registry write from a real (even bootstrap-gated) M2 run
- done-when: one real publication record exists with all required fields
- status: not started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M2: LinkedIn Auto-Publish (bootstrap-gated)
- [ ] Bootstrap gate wiring (reuse `pre_filter.py`, `gate_policy=bootstrap`), LinkedIn API publish, token-expiry alert, `SAFETY_PAUSE` circuit breaker
- verify: one real, fully automatic LinkedIn post on real data, no manual step
- done-when: Registry shows one real `gate_policy=bootstrap`/`gate_status=pass` record with a live LinkedIn URL
- status: not started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M3: Owner Verdict Capture (LinkedIn)
- [ ] Verdict event stream, `content_id`-keyed, no lifecycle coupling
- verify: a verdict recorded for a real M2 publication, and a Weekly snapshot with no verdict yet for another
- done-when: both a `recorded` and a `missing` `verdict_status` are demonstrated
- status: not started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M4: Habr Manual Outbox + Edit Capture
- [ ] Telegram draft hand-off, Google Drive credential + client (new), draft/final diff → Evidence
- verify: one real Habr draft delivered, one real owner edit captured as a diff-based Evidence record
- done-when: an Evidence record exists linking a real `-draft`/`-final` pair
- status: not started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M5: Telegram HITL Bot
- [ ] Consume ToolTempest shared transport (blocked on `[B-065]`/ADR-0051), Russian message formatting for all four responsibilities
- verify: one real send + one real receive round-trip against the owner's real Telegram chat
- done-when: an Owner Verdict, a Change Proposal approval, and a Weekly report have each been delivered and parsed correctly at least once
- status: blocked on `[B-065]`
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M6: Weekly Snapshot & Pattern Detection
- [ ] Immutable per-run snapshots, `verdict_status`, `PatternCandidate` in `OBSERVE_ONLY`
- verify: two consecutive Weekly runs, confirming the first snapshot is never overwritten by the second
- done-when: a `PatternCandidate` accumulates a real `occurrence_count` with no Change Proposal drafted while `action_policy: disabled`
- status: not started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M7: Change Proposal Mechanism
- [ ] Per-channel `prompt_version` tracks, optimistic concurrency, LLM-drafted diffs, terminal STALE
- verify: one proposal applies cleanly; one proposal (targeting an already-moved version) goes STALE and is confirmed never applied
- done-when: both outcomes are demonstrated on real (not synthetic) prompt versions
- status: not started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M8: Quality Gate (Real R6)
- [ ] Full 5-condition R6 rule, three-outcome state machine, transition-based alerting — blocked on Path B Claim Extraction (separate future `/spec`)
- verify: R6 correctly passes a real Claim meeting all five conditions and blocks one missing any single condition
- done-when: `gate_policy=R6` records appear in the Registry for new publications, with M2-M7's `bootstrap` records unchanged
- status: blocked on Path B Claim Extraction (not yet spec'd)
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## Open Questions / Decisions Needed

- Habr-multiple-articles-per-day: the `YYYY-MM-DD-draft`/`-final`
  naming convention assumes at most one Habr article per calendar day.
  If the owner ever publishes more than one on the same date, the
  convention needs a disambiguator (slug or sequence suffix) — flagged
  by the owner herself during this interview, not yet confirmed as a
  real scenario.
- Path B Claim Extraction's own design (M8's blocking dependency) is
  explicitly out of this spec's scope — a separate `/spec` interview,
  per the owner's own decision this session.
- ToolTempest's shared Telegram transport (M5's blocking dependency,
  `[B-065]`/ADR-0051) is implementation work in a different repository,
  tracked but not designed here.
- The exact real threshold values for `PatternCandidate.threshold` and
  the prompt-fix-confirmation window are deliberately not set anywhere
  in this spec (ADR-0052) — they are owner policy, set later from real
  operating data, not a default this spec should guess at.
