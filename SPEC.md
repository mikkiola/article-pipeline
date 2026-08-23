# Session-End Doc-Sync Auto-Close — Specification

## Overview

Design for a mechanism where Claude Code proposes closing `docs/BACKLOG.md`
line items and directly syncs `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/
`README.md` structural facts at natural session-completion points, using
structured commit-trailer matching (not natural-language inference) — so
the owner stops having to manually prompt "go close that BACKLOG entry" or
"update ARCHITECTURE.md" after Claude Code has already done the work each
describes. `docs/CONSTITUTION.md` is explicitly and permanently excluded
(see its own section below).

## Problem statement

By the end of a working session, all four canonical docs should reflect
what was actually done in that session without the owner separately asking
for it. Today this requires a manual, explicit prompt after implementation
— treated as a failure of the system's actual purpose, not an acceptable
manual step. This SPEC resolves that for three of the four docs
(`docs/BACKLOG.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `README.md`)
and explains, with existing architectural precedent, why the fourth
(`docs/CONSTITUTION.md`) is deliberately not included.

**Correction on this SPEC's origin, made mid-session.** The task that
opened this interview quoted a BACKLOG.md entry — "Interactive-session
doc-sync enforcement (currently purely prose-based via CONSTITUTION.md) is
an open architectural gap with no programmatic enforcement yet addressed"
— framing this interview as resolving an already-tracked gap. A full-text
and git-history search of `docs/BACKLOG.md` this session found no such
entry, current or historical. The owner confirmed mid-session: that text
came from architect-chat session notes, never written to BACKLOG.md. The
underlying problem is still real (the owner's own first-hand, repeated
experience), but this SPEC formalizes a previously-unlogged gap — it does
not close a pre-existing tracked item.

**Why this is hard.** Existing DocOps machinery (`doc_sync.py`,
`doc_sync_tier2.py`, `verify.py`, pre-commit/pre-push hooks, ADR-lifecycle
checks) enforces *structure* — are docs well-formed, does a component
change have a paired doc-update warning, and (for `docs/ARCHITECTURE.md`/
`README.md` specifically) provides a safe direct-write/snapshot/rollback
mechanism (`apply_tier2_sync()`). None of it reads prose or repo state and
determines, on its own, that a specific open task is now satisfied or that
a specific fact has changed. That detection/trigger step — deliberately
out of scope of the existing infrastructure by its own governing ADR (see
Consistency checks) — is what this SPEC designs, deliberately avoiding
natural-language matching as the trigger (see Decision 1 below).

## Scope

**In scope:**
- `docs/BACKLOG.md` — task-line-item closure at session-end, gated by
  mandatory owner confirmation.
- `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/`README.md` — structural
  fact-sync (component lists, dependency lists, file paths, phase-status
  table content — mechanically diffable content only, not narrative
  prose) at the same session-end checkpoint, written directly with no
  confirmation gate, reusing the existing `apply_tier2_sync()`
  write-safety infrastructure.

**Correction, 2026-08-22 (Metadata/ID Layer `/spec` interview).** The
original design above grouped `docs/ROADMAP.md` with `docs/BACKLOG.md`
under the confirmation-gated flow. That's wrong: `docs/ROADMAP.md` has
no line-item structure to close (it's a phase-status table plus prose,
not individually-closeable tasks the way `docs/BACKLOG.md` is), and the
Metadata/ID Layer interview explicitly decided it should get no
`[R-NNN]`-style ID and no `Closes:` trailer — the same direct-write
treatment as `docs/ARCHITECTURE.md`/`README.md`. This SPEC is corrected
accordingly below; every section that previously paired BACKLOG.md with
ROADMAP.md under the confirmation-gated design has been rewritten, not
left as a stale artifact of the original two-pass interview.

**Out of scope, and why:**
- `docs/CONSTITUTION.md` — explicitly, permanently excluded. See its own
  section below.
- Narrative/prose accuracy in `docs/ARCHITECTURE.md`/`README.md` (as
  opposed to structural facts) — would reintroduce natural-language
  judgment calls, the exact failure mode this SPEC avoids by design
  (owner decision, this session).
- Any change to CODEOWNERS or branch-protection configuration — see
  Consistency checks below; this mechanism needs none.
- The external-contributor PR flow (ADR-0033/0034/0035's territory).
  This mechanism is scoped to the owner's own first-party Claude Code
  sessions only, which already push directly to `main` (ADR-0039).

## Design decisions — `docs/BACKLOG.md` (task closure, confirmation-gated)

Scoped to `docs/BACKLOG.md` only, corrected 2026-08-22 (see the note
under Scope above) — `docs/ROADMAP.md` moved to the direct-write table
below.

| # | Question | Decision |
|---|---|---|
| 1 | **Matching** — how does the mechanism know which BACKLOG.md line a session's work closes? | Structured commit-message trailer convention: `Closes: B-NNN`, written by Claude Code as part of the commit that does the work. `B-NNN` is `docs/BACKLOG.md`'s own stable per-entry ID (Metadata/ID Layer `/spec` interview, 2026-08-22, implemented across all 34 current entries) — the placeholder `Closes: BACKLOG#<id>` in the original design is replaced by this real, concrete format now that the ID gap is resolved. No natural-language inference at match time. |
| 2 | **Trigger** — when does the mechanism act? | Session-end, anchored to the session-start plan CONSTITUTION.md's Session protocol already mandates stating. Claude Code holds accumulated trailers through the session; at a point where completed work appears to satisfy the stated plan, it proactively asks the owner whether to close now or keep accumulating. No timer, no separate `/session-end` command. **"Natural completion point" resolved:** no text-matching heuristic infers plan completion. If Claude Code is not confident the stated plan is done, it asks directly — "Is the session's stated plan done, or not yet?" — rather than guessing from plan text or commit content. Same owner-confirmation gate as decisions 2/3, not a separate mechanism. |
| 3 | **Confirmation** — is there a human gate before a doc write? | Yes, mandatory, every time. No silent auto-write. The owner's explicit reply is what triggers the doc rewrite — answered as part of decision 2, not a separate mechanism. |
| 4 | **Ambiguous match** — more than one plausible closed item? | Present every plausible candidate and wait — nothing closes until the owner picks. Must be phrased in plain language for a non-technical reader: task titles as written in BACKLOG.md (e.g. "This session's work might close either of these two tasks — [B-012] or [B-019] — which one, or both?"), never a raw ID alone without its title. |
| 5 | **Blast radius / rollback** — if a wrong auto-close lands, what's the recovery path? | `docs/BACKLOG.md` is mutable working state, not a "publication" under Immutable Lineage. A wrong closure is fixed with an ordinary follow-up edit/commit; git history is the audit trail. Immutable Lineage stays scoped to ADRs/published artifacts as already defined. |
| 6 | **Recovery — owner never replies before the session ends** (resolved 2026-08-21, via `finding-unknowns` gap check) | Accepted as a real possibility, not designed away. No new log/document is created for this — explicit owner instruction. Trailers already persist in git commit history regardless of session state, so nothing is silently destroyed; it just waits to be found. See Mechanism design step 0. |

**Feasibility note.** Nothing in the above is infeasible as stated. The
"no wrong auto-write" risk that unconstrained natural-language matching
would create is closed structurally by decision 3 (mandatory confirmation
before every write) and decision 1 (structured trailer, not NL
inference) — not by claiming perfect matching accuracy.

## Design decisions — `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/`README.md` (structural fact-sync, direct-write)

Added 2026-08-21, second interview pass, after `finding-unknowns` found
the original SPEC understated its own scope (see Source below). Reasoned
through separately from the table above, not copy-pasted onto it — these
files have different properties from `docs/BACKLOG.md` (already
direct-write today or, for ROADMAP.md, no task-line-item structure to
gate in the first place).

`docs/ROADMAP.md` added here 2026-08-22 (Metadata/ID Layer `/spec`
interview) — moved from the confirmation-gated table above, where it
was originally, incorrectly, grouped with `docs/BACKLOG.md`. Decisions
A1/A2 below were reasoned for `docs/ARCHITECTURE.md`/`README.md`
specifically but apply to `docs/ROADMAP.md` on the same logic: its
Status table's phase rows and "Current pointer" paragraph are
mechanically-diffable facts (phase status: Closed/Blocked/Not started),
not task-closure judgment calls — the same property A1 already
requires, not a new exception carved out for it.

| # | Question | Decision |
|---|---|---|
| A1 | **"Out of sync" meaning** — what does this mechanism's trigger actually check for these files? | Structural fact-sync only: component/dependency lists, file paths, phase-status table content, and similar fact-table content matching actual repo state — mechanically checkable by diffing against reality. Explicitly **not** narrative/prose accuracy (descriptive paragraphs about system behavior) — that would reintroduce natural-language judgment calls, the exact failure mode decision 1 above was designed to avoid. This mechanism can guarantee what it claims (verifiably diffable) rather than "probably accurate." |
| A2 | **Confirmation** — same mandatory gate as BACKLOG.md, or different? | Same trailer-tagging + session-end batching pattern as decisions 1–2 above, but **no confirmation gate** — Claude Code writes directly at the same session-end checkpoint, consistent with the existing direct-write precedent (`apply_tier2_sync()`, ToolTempest ADR-0004) and `docs/CONSTITUTION.md`'s "unambiguous fact update, no confirmation needed" rule. Lower risk than BACKLOG.md by design: A1's trigger is mechanically verifiable, not inferred from judgment about whether a task is "done." |

**Known gap, flagged not resolved here (found 2026-08-22, implementation
session):** ToolTempest's vendored `scripts/doc_sync_tier2.py` currently
defines `GATED_DOCS = frozenset({"docs/BACKLOG.md", "docs/ROADMAP.md"})`
— `docs/ROADMAP.md` is still marked as requiring `apply_tier2_sync()`'s
own `interactive` confirmation at the write-infrastructure level, a
different (cross-repo, ToolTempest-side) mechanism from this SPEC's own
confirmation-gate decision above. A2's "no confirmation gate" decision
for `docs/ROADMAP.md` doesn't fully take effect until `GATED_DOCS` is
also updated in ToolTempest to drop `docs/ROADMAP.md` — a separate,
cross-repo change with its own implications (ADR-0035's CODEOWNERS/
branch-protection design specifically grouped `docs/BACKLOG.md`/
`docs/ROADMAP.md` together for a *different*, GitHub-level review gate;
worth checking whether that reasoning still holds before touching
`GATED_DOCS`, not assumed either way here). Not resolved in this
session — flag before M7 is implemented.

## `docs/CONSTITUTION.md` — explicitly excluded

Owner decision, 2026-08-21: `docs/CONSTITUTION.md` stays entirely outside
this mechanism — purely owner-initiated, manual edits only, permanently.

This matches existing, deliberate, cross-repo-established precedent found
during the second interview's `finding-unknowns` pass: ToolTempest's own
ADR-0002 ("Tier 2 /doc-sync architecture"), under "Scope / Invariants",
states *"CONSTITUTION.md is out of scope for Tier 2 entirely — no direct
update, no proposal. Only a human edits it,"* and explicitly cites
`article-pipeline`'s own `docs/CONSTITUTION.md` as the precedent for that
boundary (that ADR's own text: *"Tier 1 precedent: CONSTITUTION.md is
untouchable even by Tier 2 — document role, not operation complexity, is
already the project's established axis for deciding who may write
where."*). This SPEC inherits that existing rule rather than reversing it
— no new rationale needed.

## Mechanism design — `docs/BACKLOG.md`

Scoped to `docs/BACKLOG.md` only, corrected 2026-08-22 — see the note
under Scope above. Every step below previously also mentioned
`docs/ROADMAP.md`; that file now goes through the direct-write
mechanism below instead, alongside `docs/ARCHITECTURE.md`/`README.md`.

0. **Session-start recovery check** (new step, runs before step 1):
   before stating the new session's plan, Claude Code greps recent
   commit history for `Closes: B-NNN` trailers not yet reflected as
   closed in `docs/BACKLOG.md` — i.e. trailers left over from a prior
   session that
   ended without a reply to step 4/5's prompt (crashed, window closed,
   ran out of tokens with the session never resuming). If any are
   found, Claude Code surfaces them immediately, in plain language,
   before proceeding with anything else: "Found N unresolved commit
   trailers from a previous session: [list]. Close these now?" No
   separate log/document stores this state — git history is the only
   store, per explicit owner instruction; the recovery check is a read
   (grep), not a new persistence mechanism. A session that ran out of
   tokens mid-session and later resumes *within the same session* is
   the normal case and is handled by steps 4/5 as already designed —
   this step 0 is specifically for a session that never resumes at all.
1. **Session start** (unchanged): per `docs/CONSTITUTION.md`'s existing
   Session protocol, Claude Code states the session's plan before work
   begins. This mechanism does not add a new step here — it reads the
   plan already being stated.
2. **During the session:** when Claude Code makes a commit it judges
   completes (fully or partially) a specific BACKLOG.md line, it adds a
   structured `Closes: B-NNN` trailer to that commit's message. The
   trailer only tags the commit — no BACKLOG.md edit happens at commit
   time.
3. Claude Code holds the set of accumulated trailers in session context.
4. **At a natural completion point** — when completed work appears to
   satisfy what the session's opening plan stated — Claude Code
   proactively asks the owner in plain language: "This looks like it
   completes the stated session plan. Update BACKLOG.md now, or
   continue accumulating and batch it later?" When Claude Code is *not*
   confident the plan is complete, it does not guess from plan text or
   commit content — it asks directly instead: "Is the session's stated
   plan done, or not yet?"
5. **If the owner says continue:** Claude Code keeps holding the
   trailers and re-asks at the next natural completion point, rather
   than assuming.
6. **If the owner says close now:**
   - Exactly one candidate: Claude Code writes the BACKLOG.md edit and
     commits/pushes it directly (the owner's own established
     direct-push path, ADR-0039 — no PR needed).
   - More than one plausible candidate: present all candidates in plain
     language (decision 4) and wait for the owner's pick before writing
     anything.
7. **If a closure later turns out wrong:** an ordinary follow-up
   edit/commit fixes it (decision 5) — no supersession ritual.

## Mechanism design — `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/`README.md`

`docs/ROADMAP.md` added here 2026-08-22 — see the note under Scope
above. Shares step 1's session-start and the session-end checkpoint
(step 4) with the BACKLOG.md flow above — one checkpoint, not two
unrelated prompts. At that same moment, this flow runs silently
alongside the BACKLOG.md prompt, not as a separate owner-facing
interaction:

1. **During the session:** when Claude Code makes a commit that changes
   a structural fact tracked in `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/
   `README.md` (component list, dependency list, file paths, phase-status
   table content — per decision A1), it tags that commit with its own
   structured trailer, distinct from BACKLOG.md's `Closes: B-NNN`
   trailer (exact key TBD, M1/M6 below).
2. Claude Code holds these trailers the same way it holds BACKLOG.md's
   trailer (step 3 above) — same session context, same accumulation.
3. **At the same session-end checkpoint** (step 4 above): Claude Code
   writes `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/`README.md`
   directly — no owner prompt, per decision A2 — using the existing
   `apply_tier2_sync()` write-safety infrastructure (snapshot before
   write, line-level diff, atomic apply, rollback on failure), not a
   new write path. See the "Known gap" note above (A2) regarding
   `docs/ROADMAP.md` specifically still being in ToolTempest's
   `GATED_DOCS` today.
4. **If a write later turns out wrong:** an ordinary follow-up
   edit/commit fixes it, same as decision 5's rollback model — these
   files are equally mutable working state today, unchanged by this
   SPEC.

**Not resolved in this pass:** whether step 0's session-start recovery
check (BACKLOG.md) has an equivalent for structural-fact trailers
orphaned by an interrupted session before the session-end checkpoint
fired. Not decided here — see Open questions / residual below.

## Consistency checks against existing architecture (verified this session)

- **ADR-0035** (`docs/adr/0035-pre-merge-gate-for-gated-docs.md`, read in
  full): CODEOWNERS + branch protection gate `docs/BACKLOG.md`/
  `docs/ROADMAP.md` against *external contributor* PRs, specifically to
  avoid a post-hoc gate (confirming a mutation after it already landed —
  the TOCTOU-adjacent anti-pattern ADR-0035 moved away from). This
  mechanism's confirm-then-write order (step 4 asks before step 6 writes
  anything) is pre-hoc, matching ADR-0035's own lesson — not a
  reintroduction of the pattern it rejected.
- **ADR-0039** (`docs/adr/0039-branch-protection-admin-bypass.md`, read
  in full): the owner is this repository's sole `admin`-role
  collaborator, with `enforce_admins` deliberately and permanently
  disabled — the owner's own Claude Code sessions already push directly
  to `main` without a PR, unaffected by ADR-0035's CODEOWNERS gate
  (which applies only to non-admin contributor PRs). This mechanism's
  step 6 direct-commit path is exactly that existing, established
  workflow — no new CODEOWNERS or branch-protection change is needed or
  implied by this SPEC.
- **`docs/CONSTITUTION.md`'s "unambiguous fact update" rule**: the
  BACKLOG.md flow deliberately adds a confirmation step narrower than
  that default (task-closure inference specifically, per decisions
  3/4); the ARCHITECTURE.md/ROADMAP.md/README.md flow deliberately does
  *not* add one, staying consistent with that default (per decision A2).
- **ToolTempest ADR-0002** ("Tier 2 /doc-sync architecture",
  `~/Dev/github.com/mikkiola/tooltempest/docs/adr/0002-tier2-doc-sync.md`
  — checked via targeted read of its "Scope / Invariants" section and
  cross-referenced against `scripts/doc_sync_tier2.py`'s own docstring,
  which cites the same ADR; not read top-to-bottom in full this session):
  defines `apply_tier2_sync()`'s snapshot/diff/apply/rollback
  infrastructure for `docs/ARCHITECTURE.md`/`README.md`, and states
  explicitly that module "contains no milestone-detection logic of any
  kind; that judgment happens entirely outside this code" — confirming
  this SPEC's own framing that the detection/trigger step, not the write
  mechanics, is the actual gap being designed. Also the source of the
  `docs/CONSTITUTION.md` exclusion, cited in that ADR's own section
  above.
- **ToolTempest ADR-0004** (referenced via `scripts/doc_sync_tier2.py`
  comments and the prior DocOps SPEC.md's M1 section / commit `aaff388`;
  not independently read this session): established `README.md` as a
  fourth direct-write Tier 2 doc alongside `docs/ARCHITECTURE.md`. This
  SPEC's decision A2 is consistent with, not overriding, that precedent.

## Milestones

Design only — none implemented this session.

- [x] M1 — Partially resolved, 2026-08-22 (implementation session,
      after the Metadata/ID Layer `/spec` interview unblocked it).
      **Key name and ID format, decided:** `Closes: B-NNN`, a git
      commit-message trailer, one per line if a commit closes more than
      one entry. `B-NNN` is `docs/BACKLOG.md`'s own stable per-entry ID
      (Metadata/ID Layer interview, implemented across all 34 current
      entries — see that session's Step 1). No longer scoped to
      `docs/ROADMAP.md` — see the correction under Scope above;
      ROADMAP.md's phase-status facts are direct-write, no trailer.
      **Full-vs-partial-progress distinction: still open**, not
      resolved by the ID gap closing — see Open questions / residual
      below, unchanged from the original interview. M1 is not fully
      closed until that's answered; the ID-format blocker specifically
      is.
- [x] M2 — Resolved 2026-08-22, together with M5 (same underlying
      question — see the "M2/M5" section below, right after this list).
- [x] M3 — Resolved 2026-08-22 — see the "M3" section below, right
      after "M2/M5".
- [x] M4 — Resolved 2026-08-22 — see the "M4" section below, right
      after "M3".
- [x] M5 — Resolved 2026-08-22, together with M2 — see the "M2/M5"
      section below. Not an executable test: the mechanism this
      milestone governs is Claude Code's own live-session judgment
      (decision 2 already rejected building a deterministic
      text-matching function), so "the test" is a written scenario
      checklist a session or reviewer checks behavior against, not a
      script. M4's `push_with_retry()` reuse and M7's
      `apply_tier2_sync()` integration below remain genuinely
      automatable and keep their own, separate TDD treatment when
      implemented.

## M2/M5 — Plan-completion trigger, operationally defined

Resolved together, 2026-08-22 (implementation session) — one question,
not two. M2 asks what Claude Code actually checks before the step-4
prompt; M5 asks for a test defining trigger/no-trigger cases for that
same check. Decision 2 already rejected a text-matching heuristic ("no
text-matching heuristic infers plan completion... it asks directly
rather than guessing") — so there is no deterministic function for M2
to define beyond Claude Code's own contextual judgment, applied at a
specific trigger *moment*. M5's "test" is a written scenario checklist,
not code — there's no `matches_plan()` function to unit-test, unlike
M4/M7's genuinely automatable pieces.

**Trigger moment (M2).** The check runs at the same point Claude Code
would already naturally produce a "Review report format"-style report
per `docs/CONSTITUTION.md` (i.e., whenever it's about to say "here's
what changed and what's next") — not a new timer, not a check after
every single commit. Reuses an existing behavioral checkpoint instead
of inventing one, matching this SPEC's own established pattern (decision
2's "no separate `/session-end` command," decision 6's "no new
log/document").

**What gets compared.** Claude Code's own understanding of the
session's opening stated plan (per `docs/CONSTITUTION.md`'s Session
protocol) against the human-readable titles of the `docs/BACKLOG.md`
entries covered by trailers accumulated so far this session. Ordinary
reading comprehension, not string matching — decision 2 already
forecloses an NLP heuristic here.

**Re-ask cadence after "continue"** (the actual operational gap M2
needed to close — decision 5 didn't fully specify this). "Next natural
completion point" means the next point where *new* trailer-tagged work
changes the completion picture, not literally the very next end-of-turn
report. Re-asking at every report after being told to hold off would be
a nagging repeat with no new information, not a natural checkpoint —
Claude Code holds silently through subsequent reports until either (a)
a new `Closes:` trailer lands, or (b) the owner raises it again.

**Scenario checklist (M5).**

TRIGGER (Claude Code should proactively ask):
1. Stated plan named specific `docs/BACKLOG.md` items (e.g. "fix
   B-012, close out B-019"); this session's accumulated trailers cover
   all of them; next natural report → ask "close now, or keep
   accumulating?"
2. Stated plan was open-ended ("investigate and fix whatever's
   broken"), no items named up front; one trailer accumulated; next
   natural report → Claude Code is *not* confident one trailer
   represents the whole open-ended plan → ask directly "Is the
   session's stated plan done, or not yet?" (decision 2's fallback),
   not assume yes from a single closure alone.

NO-TRIGGER (Claude Code should not prompt):
3. Stated plan named 3 items; only 1 trailer accumulated so far; next
   natural report → no prompt, plan clearly not done, keep working.
4. Owner already said "continue" earlier this session; no new trailer
   has landed since; next natural report → no re-prompt (re-ask
   cadence rule above).
5. Zero trailers accumulated this session (no `docs/BACKLOG.md` work
   happened) → no prompt; nothing to potentially close.

AMBIGUOUS MATCH (feeds decision 4 / M3, not a trigger/no-trigger case
on its own):
6. Stated plan named one item, but this session's work also
   incidentally closed a second, unstated one → present both
   candidates in plain language (M3's format), wait for the owner's
   pick — never silently guess which one(s) were meant.

## M3 — Candidate-presentation format

Resolved 2026-08-22 (implementation session). No TDD test needed here
— unlike M2/M5, this isn't a trigger-condition mechanism, it's a
phrasing/formatting convention, the same category as
`docs/CONSTITUTION.md`'s own "Response format by task type" table,
which has no automated test either.

**Template**, scaling from 2 candidates to any number:

```
This session's work might close one or more of these tasks:

1. [B-NNN] <entry's title, exactly as written in docs/BACKLOG.md>
2. [B-MMM] <entry's title, exactly as written in docs/BACKLOG.md>
...

Which one(s) should I mark done, if any?
```

**Rules, reviewed against a non-technical-reader bar:**

- The ID (`[B-NNN]`) is always shown paired with its title, never
  alone — decision 4's own rule, unchanged. The ID exists so the owner
  has a short token to reference back ("close #1" or "close B-012"
  both work), not as the primary identifying text.
- Titles are quoted exactly as `docs/BACKLOG.md` already writes them —
  that file's own style is already plain-language prose (per its own
  existing convention), not restated or summarized into new wording
  that could drift from what the entry actually says.
- No git/implementation jargon anywhere in the prompt itself: no
  "trailer," "commit," "matching," "candidate," or `Closes:` syntax
  visible to the owner. Those are Claude Code's own internal mechanism
  (decision 1), not something the owner needs to know to answer.
- "If any" is explicit in the closing question — declining to close
  anything is a normal, expected answer, not something the owner has
  to infer is allowed. Matches decision 4's "nothing closes until the
  owner picks," including picking none.
- Numbered list, not a run-on sentence — holds even at 2 candidates
  (the original decision-4 example, "which one, or both?", was fine
  for exactly 2 but doesn't scale past that; the numbered-list format
  replaces it as the one form used regardless of count, so there's a
  single consistent format rather than a special case for "exactly
  two").

## M4 — Integration point in Claude Code's session/commit flow

Resolved 2026-08-22 (implementation session). Checked
`.github/scripts/reconcile.py`'s actual `push_with_retry()` (lines
50–73) before writing this: it's self-contained — takes only
`max_attempts` (default 3), uses `run_git()` against
`git rev-parse --show-toplevel`, and has **no dependency on
`PR_NUMBER`/`MERGED_SHA`** (those env vars are read elsewhere in the
file, in the GitHub-Actions-specific `main()`, not inside
`push_with_retry()` itself). Cleanly reusable from a local Claude Code
session without faking any CI-only environment.

**Steps 0/2–6, anchored to Claude Code's actual behavior, not a new
mechanism:**

- **Step 0** (session-start recovery grep) runs as part of
  `docs/CONSTITUTION.md`'s existing Session protocol — after reading
  the four canonical docs, *before* stating the session's plan (the
  protocol already ends that sequence with "Then state the session's
  plan before starting work"; step 0 slots in immediately before that
  sentence, since orphaned trailers found there might change what the
  stated plan should even say — e.g. "close these two leftover items
  first, then start on X").
- **Step 2** (commit-time trailer tagging) is not a separate action —
  it's Claude Code including a `Closes: B-NNN` line in a commit message
  it was already about to write, exactly like any other commit-message
  content decision. No new tooling, no hook.
- **Step 3** (holding trailers) needs no integration at all — this is
  Claude Code's own conversational context for the running session, not
  a persisted data structure. Discoverable via `git log` if ever needed
  mid-session, consistent with decision 6/step 0's "git history is the
  only store" principle.
- **Step 4** (natural-completion prompt) anchors to the same
  `docs/CONSTITUTION.md` "Review report format" checkpoint M2/M5
  already define — one integration point, not a separate one for M2
  and M4.
- **Steps 5/6** (continue-holding vs. write-now) are a plain
  conditional on the owner's reply to step 4 — no new mechanism beyond
  branching on that answer, using M3's candidate format when step 6
  finds more than one plausible closure.

**Step 6's push, reusing `push_with_retry()` (not reimplementing it):**
literal reuse — import and call the function from its actual source,
not a re-derived copy of its retry/rebase logic:

```bash
python3 -c "
import sys
sys.path.insert(0, '.github/scripts')
from reconcile import push_with_retry
err = push_with_retry()
if err:
    print(f'FAIL: {err}')
    sys.exit(1)
print('OK: pushed')
"
```

Run after the `docs/BACKLOG.md` edit is committed locally (ordinary
`git commit`, same as every other commit this session already makes) —
this replaces only the final `git push`, not the commit itself. Matches
the concurrent-push race class `push_with_retry()` was built to catch
(a second session/process pushing to `main` between this session's
commit and its push) — the exact risk an unguarded `git push` in the
original design would have reintroduced.

## M6 — Structural fact-sync trigger, defined

Resolved 2026-08-22 (implementation session). Read `docs/ARCHITECTURE.md`
in full before writing this — its own stated design ("Every fact is a
table cell — no prose sections") doesn't automatically mean every cell
is A1's kind of "mechanically diffable" fact. The distinguishing test
is what A1 already says: mechanically checkable by diffing against
reality, not narrative/prose judgment — being *inside* a table cell
doesn't satisfy that test on its own.

**`docs/ARCHITECTURE.md`'s main table (Component/Status/Depends
on/Validation/Commit):**
- **In scope:** `Status` (Implemented/Not started/etc.), `Commit`
  (SHAs/ranges), `Depends on` when a new dependency is introduced —
  objective facts a task's own outcome directly determines.
- **Out of scope:** `Validation` — despite being a table cell, its
  content ("Tested on real data, 5/5 unverifiable," "Regression-tested:
  RECONCILE, HARD BLOCK...") is narrative summary/judgment, exactly
  what A1 excludes. Stays owner/architect-edited, same as any other
  prose in this project.

**`docs/ROADMAP.md`'s Status table:**
- **In scope:** the `Status` column only (Closed/Blocked/Not
  started/phase-transition facts).
- **Out of scope:** the "Current pointer" prose paragraph and the
  dependency-chain diagram — narrative, same A1 exclusion as
  ARCHITECTURE.md's Validation column.

**`README.md`: not fully resolvable yet.** `README.md` doesn't
currently have a fact-table shape at all — it's still the stale
scaffold-era file `docs/BACKLOG.md`'s `[B-003]` entry describes
(unresolved as of this session). Defining which of its facts are
in-scope depends on what shape `[B-003]`'s rewrite actually gives it;
not invented here ahead of that work. Flagged, not blocking the rest
of M6 — ARCHITECTURE.md/ROADMAP.md's scope is fully defined above.

**How it's diffed — reusing, not inventing a detection algorithm.**
Not a repo-scanning "figure out what changed" script. Claude Code,
having just done the work in-session, already knows which cell(s)
changed and to what value — the same "Claude Code's own judgment"
pattern M2 already established, not a second detection mechanism.
Claude Code supplies the proposed new table content directly (same
"contributor supplies proposed content, not generated by automation"
pattern ADR-0034 already established for the post-merge path) to
`apply_tier2_sync()`, which does the actual mechanical diff-against-
current-disk-content, atomic write, and rollback-on-failure — reusing
that infrastructure exactly as decision A2 already specifies, not
reimplementing diff logic here.

**Remaining Milestones checklist** (continuation of the list under
"## Milestones" above — M7 doesn't have its own resolved-detail section
yet, unlike M1/M2/M3/M4/M5/M6):

- [x] M6 — Resolved 2026-08-22 (README.md partially — see its own note
      below) — see the "M6" section below, right after "M4".
- [ ] M7 — Integration with the existing, vendored `apply_tier2_sync()`
      (ToolTempest) — confirm the trailer-triggered write reuses that
      infrastructure rather than reimplementing snapshot/diff/rollback,
      and define the distinct trailer key from M1's `Closes: B-NNN`.
      Must also resolve the "Known gap" flagged above (A2): ToolTempest's
      `GATED_DOCS` still includes `docs/ROADMAP.md` as of 2026-08-22 —
      confirm whether that needs a ToolTempest-side change before this
      milestone's write path can treat ROADMAP.md as truly
      confirmation-free, or whether `apply_tier2_sync()`'s `interactive`
      flag can be overridden per-call without a ToolTempest-side edit.
      Not decided; check the actual function signature before assuming
      either way.

Each milestone: status: not started. This session's task was explicitly
design-only — no implementation, no code, no other file, per the task's
own scope lock.

## Open questions / residual (not blocking, flag for the implementation session)

- Whether partial progress on a BACKLOG.md item (not full closure) also
  gets a trailer and its own prompt, or whether this mechanism is
  full-closure-only — the interview's five decisions covered closure
  matching/triggering/confirmation but didn't explicitly address partial
  progress. Not decided here; don't assume either way without asking.
- Whether the session-start recovery check (step 0, BACKLOG.md) has an
  equivalent for ARCHITECTURE.md/ROADMAP.md/README.md structural-fact
  trailers orphaned by a session that ended before the session-end
  checkpoint fired — not decided in the second interview pass; flag
  before M7 is
  implemented.

## Deferred / not this SPEC

- `docs/CONSTITUTION.md` automated updates — explicitly excluded, owner
  decision this session plus existing ToolTempest ADR-0002 precedent.
  Stays purely manual/owner-initiated, permanently — not an interim
  state pending a future revisit.
- Narrative/prose accuracy checking for `docs/ARCHITECTURE.md`/
  `README.md` — explicitly out of scope per decision A1, not something
  this SPEC understates elsewhere.
- Any CODEOWNERS/branch-protection configuration change — none needed
  (see Consistency checks above); `docs/ARCHITECTURE.md`/`README.md`'s
  existing direct-write precedent (ADR-0004) already covers this without
  new configuration.
- Implementation of M1–M7 — a separate, later session's work.

## Source

`/spec` interview, this session, 2026-08-21, in two passes.

**First pass.** Step 0 (`docs/CONSTITUTION.md`, read in full) confirmed
the SPEC.md/Living Spec model current and surfaced the session/`/spec`
protocol rules this interview followed. A discrepancy in the task's
framing (a quoted BACKLOG.md entry that does not exist in current content
or git history) was found, flagged, and corrected by the owner mid-session
before the interview proceeded — see Problem statement above. Five design
questions (Matching, Trigger, Confirmation, Ambiguous match, Blast
radius/rollback) were answered directly by the owner via one-at-a-time
questions; no infeasibility found. Design cross-checked against ADR-0035
and ADR-0039 (both read in full) for consistency with existing gated-doc
architecture — no conflict found.

**Gap check, between passes.** `finding-unknowns` run directly against
the finished first-pass SPEC.md, checked against the owner's original,
broader stated goal ("all canonical docs... automatically"). Found: (1)
no-reply-before-session-end behavior undefined — owner resolved, folded
in as decision 6 / mechanism step 0; (2) interrupted-session trailer
recovery unspecified — folded into decision 6 / step 0's design (git
history as the only store, no new log file, per explicit owner
instruction); (3) a concurrent-push race in the direct-commit path
(step 6) has no described handling, unlike `reconcile.py`'s hardened
`push_with_retry()` — flagged for M4, not yet resolved; (4) the first
pass's claim that `docs/ARCHITECTURE.md`/`README.md`/`docs/CONSTITUTION.md`
were "already handled by existing CONSTITUTION.md rules" was checked
against `docs/BACKLOG.md`'s "pre-push component/doc pairing check stays
warning-only permanently" entry and found **false** — only a prose policy
plus a deliberately non-blocking structural check exist, not enforced
sync. This directly motivated the second pass.

**Second pass.** `pre-spec` routed to both `phrase-decomposer` and
`finding-unknowns` on the expanded scope (owner-directed, treating this as
a genuine new architectural fork, not a copy-paste extension).
`phrase-decomposer`: BLOCKING — "out of sync" bundles structural-fact-sync
and narrative-prose-sync as distinct meanings for `docs/ARCHITECTURE.md`/
`README.md`; resolved by asking per-document rather than as one merged
question (interview Q1). `finding-unknowns`: 3 findings, all resolved on
direct code/ADR reads this session (`scripts/doc_sync_tier2.py`,
ToolTempest ADR-0002's "Scope / Invariants" section) — no BLOCKING, but
materially reframed what the interview should ask (see Consistency
checks). Three questions then asked one at a time, all answered by the
owner: out-of-sync meaning (A1, structural-fact-sync only), confirmation
treatment (A2, no gate, matches ADR-0004 precedent), and `docs/CONSTITUTION.md`'s
exclusion (confirmed, matches ToolTempest ADR-0002 precedent). Folded into
this same SPEC.md as its own clearly-labeled sections, per owner
instruction — existing BACKLOG/ROADMAP decisions and mechanism steps left
unmodified except for the step-0/decision-6 addition from the gap check.

Separately during the first pass, at the owner's explicit confirmation,
three local Claude Code skills (`pre-spec`, `phrase-decomposer`,
`finding-unknowns`) were relocated from `~/.claude/skills/user/<name>/`
to `~/.claude/skills/<name>/` to fix a loader path issue — a local
environment change, unrelated to and outside this SPEC's scope, noted
here only for session continuity. Both sensor skills used in the second
pass are the same three relocated then.

**Correction pass, 2026-08-22.** Implementation session, resuming M1
after the Metadata/ID Layer `/spec` interview (same date) gave
`docs/BACKLOG.md` real per-entry IDs (`[B-NNN]`), unblocking the
`Closes: BACKLOG#<id>` placeholder. While resolving M1, found that the
original design's grouping of `docs/ROADMAP.md` with `docs/BACKLOG.md`
under the confirmation-gated flow directly contradicted that same
interview's own decision (ROADMAP.md gets no ID, no trailer, no
confirmation gate — the ARCHITECTURE.md/README.md direct-write
treatment instead). Flagged to the owner rather than silently patched;
owner confirmed: restructure now, not defer. Every section that had
paired BACKLOG.md/ROADMAP.md under the confirmation-gated design was
rewritten — Scope, both decision tables, both mechanism-design
sections, the Consistency checks bullet on `docs/CONSTITUTION.md`'s
"unambiguous fact update" rule, and the Open questions section.
Historical Source entries above (first/second pass, 2026-08-21) were
left unedited as an accurate record of what was decided and reasoned
at the time — this correction did not retroactively rewrite them.

While restructuring, a second, deeper gap was found and flagged (not
resolved): ToolTempest's vendored `scripts/doc_sync_tier2.py` still
defines `GATED_DOCS` to include `docs/ROADMAP.md` — a cross-repo,
write-infrastructure-level gate distinct from this SPEC's own
confirmation-gate decision, that doesn't automatically follow from
correcting this SPEC's prose. Noted under the direct-write table (A2)
and folded into M7's remaining scope, not resolved here — a
cross-repo change, if needed, is its own decision.

M1 itself: the key name (`Closes:`) and ID format (`B-NNN`) are now
decided and reflected throughout. The full-vs-partial-progress
question M1's original wording also named remains genuinely open,
unaffected by the ID gap closing — not resolved in this pass, left as
its own item under Open questions / residual, unchanged.
