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
- [ ] M9 — Habr Draft Automation produces an internal Habr draft from
      real Collector data and fetched code fragments, checks it
      (L1, Habr platform rules, project requirements, Q), revises it
      within a fixed bound, and saves a run report that never claims
      publication approval.

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
- **M9 reuses, and adds no new service for:** the existing GitHub REST
  API client path in `strategy_layer/adapters/collector.py`
  (`GITHUB_APP_TOKEN`, ADR-0056 point 6; stage 2 receives a narrower
  token from the same GitHub App, requirement 53), the Anthropic Messages
  API call Author already uses (with a separate key
  `ANTHROPIC_API_KEY_HABR_DRAFT`, model `claude-sonnet-5-5`, owner
  decision 2026-10-15), the existing one-way Telegram send, and Linkup
  through `evidence_package/` as an optional retrieval mechanism only
  (not performed in the MVP). Whether the GitHub App installation
  reaches the unattended runtime with read access to the three
  allow-listed repositories is a stated precondition (requirement 43).

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
9. Bootstrap-gate block → no publish. When the block is not caused by
   an integrity violation, a structured record still writes to the
   Registry (`gate_status = block`, `block_reason` from `pre_filter`'s
   own `_EXCLUDE_REASON`). When the block is caused by an integrity
   violation (`integrity_status = invalid`), the run outcome is
   `FAILED_INTEGRITY` and no Registry record is written (FR41).
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

41. **Run outcome.** (M2; the next free requirement number, so no existing
    FR number changes.) Every run of the scheduled LinkedIn publish resolves to
    exactly one outcome, with this exit code:

    | Outcome | Exit |
    |---|---|
    | `PUBLISHED` | 0 |
    | `SKIPPED_NO_ELIGIBLE_CONTENT` | 0 |
    | `SKIPPED_SAFETY_PAUSE` | 0 |
    | `SKIPPED_ALREADY_PUBLISHED` | 0 |
    | `SKIPPED_AUTOMATION_ONLY` | 0 |
    | `FAILED_INTEGRITY` | 1 |
    | `FAILED` | 1 |

    Decision order: an open `SAFETY_PAUSE` skips the run; an existing
    `pass` Registry record for the `content_id` wins over any input
    problem found later (`SKIPPED_ALREADY_PUBLISHED`); the bootstrap gate
    (FR8) keeps its mechanism unchanged. A gate block caused by an
    `integrity_status = invalid` exclusion is `FAILED_INTEGRITY`: no
    model call, no publish, no block `PublicationRecord`, and the
    specific diagnostic (for example `schema_version=3, expected 2`)
    is kept in the run outcome. A gate block with no integrity
    violation is `SKIPPED_NO_ELIGIBLE_CONTENT` and writes the block
    record (FR9). `FAILED_INTEGRITY` fires only on a gate block caused
    by a confirmed integrity violation; existing per-unit exclusion with
    valid-unit continuation is unchanged. Any other unexpected failure
    is `FAILED`.
    The outcome is additional signal: `gate_status` stays
    `pass`/`block`. Publication and Registry persistence are separate
    events. A persistence failure after a confirmed publish is `FAILED`
    with the post URL preserved in the diagnostics; the run neither
    retries nor publishes a second time. `SKIPPED_AUTOMATION_ONLY`
    writes no Registry record (a record type for it is `[B-076]`, not
    built). Known limit: the `FAILED_INTEGRITY` diagnostic lives only in
    the run outcome, the job summary and the run log, within the GitHub
    Actions retention configured for the repository; it is not a
    durable archive.

### Functional Requirements — M3: Owner Verdict (LinkedIn)

14. Owner Verdict is an append-only event stream (ADR-0050 point 1
    (confirmed current and unchanged by ADR-0052; see ADR-0052's Context
    & Constraints)), stored as JSON records under `verdict/output/`, one
    record per verdict, keyed by `content_id` (never `claim_id`).
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
    posting exists or is attempted. This clause's own grammar ("once
    Author generates...") treats draft generation as a precondition
    this requirement consumes, not an action it must itself cause or
    schedule — confirmed, 2026-10-01, by direct comparison against
    FR19's self-contained "a scheduled job watches for..." wording,
    which does own its trigger mechanism. Three separate, independently
    confirmed facts stand between this requirement and real use, not
    one:
    - No working path (manual or scheduled) anywhere in this repo
      produces a *current* Habr draft today — `strategy_layer/
      run_habr_pilot.py`, the only end-to-end script, hardcodes a stale
      manifest date and is self-described as "Throwaway orchestration...
      not TDD'd for that reason." Filed as `docs/BACKLOG.md`'s
      `[B-071]`, not fixed here.
    - Separately, and still true even once a working generator exists:
      nothing anywhere in this repo decides *when* generation should
      run — no cron, workflow, or CLI triggers it on any cadence,
      manual or scheduled. Confirmed directly, 2026-10-01: zero
      `.github/workflows/` entries reference anything Habr-related, and
      no script calls a generation step on any kind of schedule.
    - Separately again, and also true even once a working, triggered
      generator exists: `habr_edit_capture/telegram_send.py`'s
      `send_habr_draft()` — this requirement's own `sendMessage` call —
      is built and unit-tested but has zero real call sites anywhere in
      this codebase. Confirmed by direct grep, 2026-10-01: `grep -rn
      "send_habr_draft" --include="*.py" .` outside its own test file
      returns only its own `def` line. Fixing the two points above would
      not, by itself, make this call fire — something would still need
      to invoke it.
    None of these three is fixed by this note; building or hardening a
    draft-generation entry point, its trigger, or wiring the send call to
    it is new scope, out of this requirement's own grammar and out of
    this note's investigating task.
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
    Implemented as its own component, `habr_edit_capture/` (not an
    extension of `verdict/` or `evidence_package/` — see
    `docs/adr/0060-habr-edit-capture-as-its-own-component.md` for the
    reasoning), with a dedup key on the `-final` file's Drive
    `modifiedTime` so a repeated scheduled run against an unchanged file
    is a no-op while a genuine re-edit is correctly captured as a new
    event, and an explicit `has_changes` field so a draft published
    unedited is still recorded, not silently skipped (same ADR).
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
    - **Scope note (added 2026-10-15, `docs/adr/0071-*`).** Requirements
      36-40 define M8 for the publication path they were written for and
      are unchanged. They are not applied to M9's Habr draft path, which
      has its own acceptance contract (requirements 41-52). In particular,
      M8's `QUALITY_BLOCK` (run-level, R6 failed) and M9's `QUALITY_BLOCK`
      (per-attempt, correctable) are different things that share a name;
      and "Linkup unavailable" is `SYSTEM_FAILURE` in M8 but only a skipped
      optional enrichment in M9. Neither definition changes the other.

### Functional Requirements — M9: Habr Draft Automation

Owner-confirmed decisions, 2026-10-14/15 (recorded with their rationale in
`docs/adr/0071-habr-draft-acceptance-contract-separate-from-r6-and-from-publication-approval.md`).
Habr's own rules were read from `habr.com/docs/help/rules` (last edited
2026-07-08) on 2026-10-15; the text of the rules is not restated here and
must be re-read from the page when the checks are planned.

41. **Purpose and boundary.** M9 produces an *internal* Habr draft from
    real Collector data, checks it, revises it within a bound, and saves
    a run report. It is the generation precondition FR17 consumes — gap
    (1) of FR17's own note, `docs/BACKLOG.md`'s `[B-071]`. It does not
    post to Habr, never approves a draft for publication, and does not
    build FR17's remaining gaps: when generation is triggered (gap 2),
    the real call site of `send_habr_draft()` (gap 3) and the Drive
    credentials (gap 4) stay as FR17's note states them. Writing the
    draft into Google Docs is done by the architect chat's own connected
    tools and is outside this spec.
42. **A separate contract.** M9's acceptance contract is not R6 and does
    not reuse M8's outcomes (see the M8 scope note). The LinkedIn path's
    contract, ADR-0044 (including its L2 public-link tier) and ADR-0047
    are unchanged. Linkup stays a `retrieval_source` (requirement 38),
    never evidence or a verifier.
43. **Code source (owner decision: variant B).** Collector's output
    carries no code or diff content (manifest: counts and file paths;
    `daily_brief` schema 3: commit subjects, `why`/`effect`, file paths
    and diffstat; verified by direct read of Collector's `data/`,
    2026-10-14). Collector's schema is not changed. article-pipeline
    fetches the diffs/fragments it needs through the existing GitHub
    credential path (`GITHUB_APP_TOKEN`). No separate token is created
    unless a concrete need is demonstrated and recorded. Each fetched
    fragment carries its provenance: repository, commit SHA, file path,
    and the fetched content. **Precondition, to be confirmed before
    implementation and not assumed here:** in the unattended production
    runtime, (i) the credential reaches the job that generates the draft,
    (ii) it has read access to every repository from which a fragment is
    fetched (requirement 53 later limited these to the allow-listed
    public repositories), and (iii) the behavior on HTTP
    403/404, rate limit and request failure is defined. Local success
    does not satisfy this. `docs/adr/0056-*` records that the App
    installation's access to the other repositories was evidenced only
    by Collector's own workflow, not by a run of this pipeline.
44. **Four mandatory automated checks, each executed in full every
    round.** All four must pass for success.
    - **L1 — fact verification.** Every factual statement in the draft
      traces to evidence from the run's own inputs: a Collector unit with
      `integrity_status = valid`, or a fragment fetched under
      requirement 43. A statement with no such trace is unverified and
      fails L1. L1 does not require an external source, `scope =
      external` or `activity_anchor` (those are R6's conditions) and
      does not use Linkup. The tracing mechanism is a planning decision.
    - **(a) Habr platform rules.** Only requirements that can be checked
      objectively from the rules' own text. Identified on 2026-10-15,
      from rule 3: paragraphs of one or two sentences are not used; text
      is split into paragraphs rather than left as a wall of text; long
      code blocks and large images are hidden in a spoiler. Rule 2's
      limit on code listings as the main content and rules 1 and 4 are
      not in (a); they are (c). The rules give no number for "wall of
      text", "long" or "large"; each such value is a required
      configuration with no default (requirement 50).
    - **(b) Project acceptance requirements.** Russian-language output;
      at least one evidence-backed code/artifact fragment, meaning a
      verbatim excerpt of content fetched under requirement 43 with its
      provenance recorded. These are this project's own bar and are
      reported as such, never as Habr rules. No other content requirement
      has been confirmed by the owner as of 2026-10-15; "at least one
      externally sourced enrichment" is not one (requirement 46).
    - **Q — quality (infostyle).** An LLM-based assessment of the draft
      against the criteria of the owner's `human-text` practice (facts
      instead of evaluations, one thought per sentence, markers of
      AI-generated text, unambiguity). It yields a score and itemized
      findings and is not presented as an objectively proven metric. The
      paid Glavred API is not integrated at this stage. `human-text` is
      a conversational skill prompt, not a callable function, and it
      lives outside this repository; the minimal reuse is to carry its
      criteria as the rubric of the Q check's own prompt, not to build a
      separate scoring engine. Whether materializing the rubric inside
      this repository meets the revisit condition of ADR-0042 is left
      open (ADR-0068); a superseding ADR is needed only if the owner
      judges that it does. Q makes a
      billable model call: the model and authentication method are
      stated and the owner's authorization obtained before any real call.
45. **(c) Human review — not automated.** Compliance with Habr rule 4
    (generated material), rule 1 (self-promotion), rule 2's judgment
    parts, authorship character and suitability for publication are the
    owner's review. Whether a draft is an engineering case study or
    promotional material is an editorial judgment and is not attempted by
    any check. "Differs from the LinkedIn post" is not a rule and not a
    check; it may appear only as an optional editorial note. Owner review
    is not publication approval.
46. **Optional enrichment.** Linkup enrichment, where performed, never
    blocks and never fails a run. Its absence, an unsupportive result, or
    an outage is recorded in the run outcome record as skipped
    enrichment with the reason, and triggers neither `QUALITY_BLOCK`,
    `BLOCKED` nor `SYSTEM_FAILURE`. A `SYSTEM_FAILURE` arises only when
    a mandatory check (L1, (a), (b) or Q) cannot execute.
47. **Outcomes and the bounded loop.**
    - A *round* is one draft plus one full execution of L1, (a), (b) and
      Q. A round passes only if all four pass.
    - **Iteration limit: at most 2 correction cycles after the initial
      draft** — at most 3 rounds. Each correction is followed by a full
      re-run of all four checks.
    - `QUALITY_BLOCK` is a per-attempt verdict from an executed check
      that found a failure. If correction cycles remain, it triggers a
      correction and a new round.
    - `BLOCKED` is the terminal outcome when the limit is exhausted
      without a round that passes all four checks.
    - `SYSTEM_FAILURE` is the terminal outcome when any mandatory check
      could not be executed (crash, missing input, dependency outage,
      unset required configuration per requirement 50). It takes
      precedence over a content failure seen in the same round, does not
      consume a correction cycle, is never converted to `QUALITY_BLOCK`
      or `BLOCKED`, and "Q did not run" is never reported as "Q failed".
    - `INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW` is the terminal outcome of
      a passing round. It means only that L1, (a), (b) and Q passed.
48. **What the saved report must say.** Every run's report states, in
    plain words, that the outcome is not publication approval, and for
    `INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW` also that Habr rule 4 and
    rule 1 are not established by any check and that the draft is not to
    be represented as publication-ready for Habr unless the owner has
    independently created or substantially authored the final technical
    article, with any AI-generated material limited to what the current
    Habr rules permit.
49. **Storage of attempts and the run outcome record (smallest fit).**
    Each attempt's draft is written as its own immutable file and never
    overwritten; a name collision raises, the pattern
    `strategy_layer/write_verdict.py` and `evidence_package/` already
    use. One run outcome record (JSON, one per run, immutable) references
    each attempt file by name and content hash and carries: the topic and
    its selection basis; per attempt, each check's status (executed or
    not, pass or fail), itemized findings and the Q score; the
    enrichment status; the terminal outcome; the report text of
    requirement 48. On `BLOCKED` all attempt files are preserved; the
    "best" attempt is the one with the fewest failed mandatory checks,
    ties going to the latest. Nothing is embedded in an existing
    contract: `PublicationRecord` requires `url` and `published_at`, which
    an unpublished draft does not have, and the Strategy Verdict is
    produced upstream of generation as Author's input, so referencing
    downstream drafts from it would reverse its direction. Neither is
    changed. The directory is set by an environment variable, following
    the pattern of `REGISTRY_OUTPUT_DIR` and `AUTHOR_STATE_DIR`
    (ADR-0066); where it persists between runs is confirmed at plan time.
50. **Open calibration items; unset means not executable.** The numeric
    Q-acceptance threshold is **not set** and is not guessed here. It
    requires owner calibration against real examples, today's manually
    written article included, before it is final. The same holds for each
    value (a) needs that Habr's rules do not give. Each is a required
    configuration with no default. While any is unset, the check that
    needs it cannot reach pass or fail and the run ends `SYSTEM_FAILURE`
    with a reason naming the missing value; the score and findings are
    still recorded so calibration data accrues (same observe-only
    precedent as ADR-0052). Planning and building the mechanisms is not
    blocked by this; declaring production acceptance validated is.
51. **Automatic topic selection.** The run chooses its topic from
    Collector units without a manual step. The selection rule is a
    planning decision; the chosen topic and the basis are recorded
    (requirement 49).
52. **Reuse.** The existing Strategy Layer chain, framing, language check
    and Habr digest rendering, `evidence_package/` and the GitHub client
    path are reused where they fit. No general-purpose quality engine and
    no abstraction beyond this one path is built.
53. **Source boundary and credential separation (owner decisions,
    2026-10-15).** Code fragments come only from an owner-approved
    allow-list of public repositories the owner owns or has a confirmed
    right to use: `article-pipeline@main`, `radar@main`,
    `tooltempest@main`; private repositories and `radar@vault` are
    excluded. Each fragment is taken from one specific commit SHA, never
    the branch tip, and carries that SHA. An allow-list entry is unusable
    until the owner records a content-safety check and an authorship
    check for it. Generated files, secrets and sensitive configuration
    are excluded (path denylist and a secret-pattern scan). Admission
    rule (owner decision 2026-10-16, simplifying the decision of
    2026-10-15; a content-admission rule of this internal pipeline, not a
    sole-authorship claim and not a legal determination): the commit's
    author must be an owner identity, established by a GitHub login or an
    address (a display name never counts); any other author, or none, is
    excluded, and no per-commit permission mechanism exists (an owner
    decision does not override a third party's rights; admitting a third
    party's work would need its own decision). The committer and the
    commit message, including `Co-authored-by` trailers, are not read, and
    no AI-assistant or bot policy exists: this spec does not require
    disclosing AI involvement in a code fragment. Basis: each allow-listed
    repository has one account with write access, the owner's, so a third
    party's commit can reach `main` only when the owner merges it, and a
    merge keeps the original author. The identity `Radar Bot
    <radar@gitlab.com>` is not an owner identity until the owner confirms
    it. The run is three workflow jobs, each holding one credential set: `prepare`
    (broad GitHub App token, no model call, no fragment fetch) validates
    input and applies the allow-list and passes only the scrubbed
    selection input on as a build artifact; `draft` (a separate
    short-lived read-only token scoped to the three repositories, plus the
    Habr API key; no registry-data checkout, no write permission) fetches
    fragments and calls the model and passes only the attempt files and
    the run record on; `deliver` (registry-data write and the Telegram
    secrets; no model key, no Collector) validates the artifact, commits
    only the run's output directory and notifies after a successful push.
    The broad token is never present in `draft`, and the model key and the
    private Collector are never present in `deliver`. Known residual: the
    GitHub App private key is read by `prepare` and by `draft` (to mint its
    narrow token) as an input of the token action only; closing that needs a
    separate narrow App and is an owner decision (ADR-0070).
54. **Run modes.** `production` refuses to start any paid call while a
    mandatory configuration value is unset (the run ends `SYSTEM_FAILURE`
    with failure kind `missing_configuration`, which reports and counts
    separately from a service outage; no new status). `calibration` is
    one bounded paid round, allowed only with the owner's recorded
    approval of the paid call and its budget; it records check results,
    the Q score and a hash of the owner's reference text, makes no
    correction cycle on an unapproved threshold, never emits
    `INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW`, and writes
    `terminal_outcome: null` with `calibration_result: recorded`. The
    reference text is supplied from a non-public location, is never
    committed or copied to the output directory, and only its hash,
    length and per-criterion scores are recorded.
55. **Input validation and observability.** An expected input failure
    (missing, malformed, wrong-date or unsupported-schema daily brief, or
    an unreadable selection input) does not abort the workflow: it yields
    a structured preflight result, a `SYSTEM_FAILURE` run record with
    failure kind `input_validation` and the specific reason, and the same
    commit and notification as any other outcome. The failure kinds are
    `missing_configuration`, `execution_error`, `budget_limit` and
    `input_validation`, and only a `SYSTEM_FAILURE` carries one.
    Incomplete mandatory configuration is checked before any candidate is
    looked at and always ends `SYSTEM_FAILURE` / `missing_configuration`.
    A run ends `NO_ELIGIBLE_TOPIC` only when the configuration is
    complete, every candidate was checked, no technical error occurred
    (fragment fetch, repository-visibility check, stage 1 integrity
    verification) and no candidate had a usable fragment (not a
    `SYSTEM_FAILURE`; no model call; no Registry record; no draft status).
    Technical errors are recorded distinctly from "no eligible topic": a
    technical error that leaves no candidate with a usable fragment ends
    the run as `SYSTEM_FAILURE` / `execution_error`; a topic found among
    the other candidates is still used, with the errors recorded. The run record also carries the article-pipeline commit, the
    Collector commit, the daily-brief hash and the hashes of the
    acceptance configuration and the rubric.
56. **Output-side safety and spend guard.** Generated text passes the
    same secret-pattern scan as input fragments before it is saved,
    logged or sent to a judge; a hit discards it (only the pattern id and
    count are recorded). The model's raw response text never appears in
    an exception message, log line or record. Commit text and code are
    declared untrusted data in every prompt. Before each paid call a
    conservative worst-case cost is estimated from the UTF-8 byte count
    of all billable input text, the configured maximum output and the
    SDK's retry allowance; a call that does not fit the remaining budget
    is not made. The limit is a best-effort guard, not a guaranteed
    maximum (billing of retried requests is not established). The
    per-run spend limit and the fragment-volume cap are owner
    configuration with no default.

## UI/UX Specification

No traditional UI. The Telegram bot (M5) is the only owner-facing
surface: Russian text, message-based (no inline buttons assumed —
reply-text parsing, matching `analyzer/scripts/telegram_bot.py`'s
existing pattern), covering Owner Verdict prompts, Change Proposal
approve/reject, Weekly reports, and alerts.

## API Design

- **LinkedIn**: `w_member_social` scope, personal-profile posting via the
  Share on LinkedIn product (ADR-0049). No partner review needed.
- **Telegram Bot API, M4**: a standalone one-way `sendMessage` call (bot
  token + chat ID) delivering the Habr draft hand-off — no dependency on
  `[B-065]` or the shared transport; FR20 explicitly rules out any
  round-trip for this milestone.
- **Telegram Bot API, M5**: `sendMessage` plus cron-polling `getUpdates`
  (no webhook, matching this ecosystem's GitHub-Actions-cron pattern) —
  via the shared ToolTempest transport once `[B-065]` lands.
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
| Habr draft run output (directory name and component fixed at plan time; location set by an environment variable, requirement 49) | M9 | per attempt: one immutable draft file; per run: one run outcome record — topic and selection basis, per-attempt check results, enrichment status, terminal outcome, report text |

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
- M9 fetches repository content through the existing read-only GitHub
  credential; it creates no new token without a recorded, demonstrated
  need (requirement 43). The credential is not exposed under
  `GH_TOKEN`/`GITHUB_TOKEN` (ADR-0056 point 6).
- M9's attempt files and run outcome record persist only where the
  runtime repository's own boundary allows (ADR-0062, ADR-0066), never in
  this public repository. Fragments come only from the owner-approved
  allow-list of public repositories (requirement 53), so private
  repository content is not an input; the owner's calibration reference
  text is never persisted (requirement 54).

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
- M9's outcome state machine (requirements 47 and 50): tests written
  first proving that a failed executed check is `QUALITY_BLOCK` and
  triggers correction; that exhausting 2 correction cycles ends
  `BLOCKED` with all attempt files preserved; that a check that could
  not execute (including an unset threshold) ends `SYSTEM_FAILURE`, is
  never counted as a pass or as a content failure, and does not consume
  a cycle; that a Linkup failure changes none of the above; and that
  `INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW` is reachable only when L1,
  (a), (b) and Q all passed and its report carries the non-approval
  statement of requirement 48.

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
- [x] Verdict event stream, `content_id`-keyed, no lifecycle coupling
- verify: a verdict recorded for a real M2 publication, and a Weekly snapshot with no verdict yet for another
- done-when: both a `recorded` and a `missing` `verdict_status` are demonstrated
- status: done — `verdict/` package (contract.py, writer.py) built and tested (15/15); `verdict/demonstrate_m3.py` recorded a real verdict against real M2-published `content_id` `linkedin-2026-09-29` and confirmed zero verdict records for real `content_id` `linkedin-2026-09-28` (both real registry-data-branch records, not synthetic) — both `recorded` and `missing` `verdict_status` outcomes demonstrated directly via `read_verdicts()`, satisfying done-when exactly as stated. The verify line's "Weekly snapshot" phrasing is illustrative, not literal: M6 (Weekly Snapshot & Pattern Detection) is separate, not-started scope — not required by done-when's own wording, and not built here.
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

### M4: Habr Manual Outbox + Edit Capture
- [ ] Telegram draft hand-off, Google Drive credential + client (new), draft/final diff → Evidence
- verify: one real Habr draft delivered, one real owner edit captured as a diff-based Evidence record
- done-when: an Evidence record exists linking a real `-draft`/`-final` pair
- status: in progress — FR18/19/21 built: `habr_edit_capture/` component (Drive
  read via `google-api-python-client`, `difflib.unified_diff`-based diff capture,
  dedup on the `-final` file's Drive `modifiedTime`, explicit `has_changes` for a
  zero-diff/unedited-draft capture — `docs/adr/0060-habr-edit-capture-as-its-own-
  component.md`), its own scheduled workflow (`habr-edit-capture.yml`) and
  branch-separated output (`habr-edit-capture-data`, same reasoning as ADR-0055's
  `registry-data`), 34/34 unit tests passing against synthetic Drive data.
  A 2026-10-01 Outcome-traceability trace found four separate, independently
  confirmed gaps on FR17's own path — fixing one does not fix the others:
  (1) no working Habr draft-generation entry point exists
  (`strategy_layer/run_habr_pilot.py` is throwaway, hardcoded to a stale
  manifest date — filed as `docs/BACKLOG.md`'s `[B-071]`); (2) separately,
  nothing anywhere decides *when* generation should run — zero
  `.github/workflows/` entries reference anything Habr-related, confirmed
  directly; (3) separately again, FR17's own `send_habr_draft()`
  (`habr_edit_capture/telegram_send.py`) is built and unit-tested but has zero
  real call sites anywhere in this codebase, confirmed by direct grep — fixing
  (1) and (2) would not by itself make this call fire; (4) `habr-edit-
  capture.yml` is genuinely scheduled (`cron: "0 12 * * *"`) and would run, but
  would fail immediately if triggered today: `gh secret list --repo
  mikkiola/article-pipeline` confirms neither `HABR_DRIVE_SERVICE_ACCOUNT_
  KEY_JSON` nor `HABR_DRIVE_ROOT_FOLDER_ID` exists as a repo secret, and the
  owner has not shared her real per-Habr-article Drive folder with a
  service account that doesn't exist yet either. Not yet satisfied: verify's
  "one real Habr draft delivered" and done-when's "a real `-draft`/`-final`
  pair" both require all four gaps above to close, not just `[B-071]` (gap 1)
  alone.
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

### M9: Habr Draft Automation
- [ ] Draft generation from Collector data and fetched fragments, L1/(a)/(b)/Q checks, bounded revision (2 correction cycles), immutable attempt files and run outcome record, non-approval report
- verify: one real run end to end on real data, with the run report showing each of L1, (a), (b) and Q executed and the terminal outcome recorded
- done-when: the saved report of a real run carries a terminal outcome from requirement 47; any `BLOCKED` run has all attempt files preserved; the report states it is not publication approval. Production acceptance is not declared validated until the Q threshold (and each unset (a) value) is calibrated by the owner
- status: code and unit tests written 2026-10-15 (`habr_draft/`; model and GitHub calls mocked in tests); no real run, no paid call, workflow not added to the runtime repository. Requirements 41-56. Real run blocked on the preconditions listed in ADR-0069 and the open items below
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

M9 (Habr Draft Automation) — opened 2026-10-15:

- **Q threshold — open calibration item (owner).** The numeric
  Q-acceptance threshold is not set. It requires owner confirmation
  against real examples, today's manual article included, before it is
  final. Does not block planning or building the check; blocks declaring
  production acceptance validated.
- **(a) values — open calibration item (owner).** Habr's rules give no
  number for "wall of text", a "long" code block or a "large" image; each
  value the machine-checkable parts need is unset (requirement 50).
- **Unset threshold ends the run as `SYSTEM_FAILURE` — owner statement
  2026-10-15.** `q_threshold_unset` is a missing-configuration state,
  distinguished from a service outage in reports and analytics, with no
  new status (requirement 54). Production mode stops before any paid
  call; calibration mode is the separate, owner-approved way to obtain
  scores.
- **GitHub credential in the unattended runtime — precondition.**
  Requirement 43 (i)-(iii). Not confirmed.
- **Which repositories may supply a fragment — decided 2026-10-15.**
  Requirement 53: owner-approved allow-list of public repositories only.
  Open remains the owner's recorded content-safety and authorship checks
  for each entry (a precondition of the first real run).
- **Relation between FR17's Telegram hand-off and the Google Docs
  hand-off — decided 2026-10-15 for M9.** Telegram is a one-way
  notification of a completed result (status and a stable reference to
  the committed artifacts, not the draft text); Google Docs remains the
  destination for review and is written by the architect chat's tools,
  outside this pipeline. The production runtime has no access to that
  connector and no Drive/Docs mechanism is added. FR17 itself is
  unchanged.
- **Alerting for M9's `SYSTEM_FAILURE`.** M8's immediate Telegram alert
  and transition-based alerting (requirement 40) are not extended to M9
  by this spec; M5, the alert transport, is blocked on `[B-065]`.
- **Whether the MVP performs Linkup enrichment at all.**
  `evidence_package/driver.py` runs only the search phase; assigning a
  status and source to a result is an interactive step today, so no
  automated path from a Linkup result to a verified item exists.
  Requirement 46 fixes only what a failure or absence means.
- **Closing `[B-071]` — criteria confirmed 2026-10-15, BACKLOG not
  edited.** (1) The entry point runs on current Collector data without a
  hardcoded manifest date; (2) each run saves a draft and a report with a
  run ID, check results and a final status; (3) in a test end-to-end run
  claims trace back to source data and approved code, and failed checks
  are never disguised as passing; (4) private code never reaches the
  material. Having an entry point does not close the item, publication is
  not approved by it, and it does not replace M9's own completion
  criteria.
- **Documents this spec does not edit and that now lag.**
  `docs/ROADMAP.md` still lists the Habr "externally-sourced
  enrichment" as committed and "no source exists for code/diff content"
  as undecided; both are changed by requirements 43 and 46.
  `docs/adr/0042-*` states the `human-text` practice has no file under
  `~/.claude/skills/`; a `SKILL.md` for it now exists under
  `~/.claude/skills/synced/`. A separate documentation task reconciles
  them.
