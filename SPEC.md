# Session-End Doc-Sync Auto-Close — Specification

## Overview

Design for a mechanism where Claude Code proposes closing `docs/BACKLOG.md`/
`docs/ROADMAP.md` line items and directly syncs `docs/ARCHITECTURE.md`/
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
- `docs/BACKLOG.md`/`docs/ROADMAP.md` — task-line-item closure at
  session-end, gated by mandatory owner confirmation.
- `docs/ARCHITECTURE.md`/`README.md` — structural fact-sync (component
  lists, dependency lists, file paths — mechanically diffable content
  only, not narrative prose) at the same session-end checkpoint, written
  directly with no confirmation gate, reusing the existing `apply_tier2_sync()`
  write-safety infrastructure.

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

## Design decisions — `docs/BACKLOG.md`/`docs/ROADMAP.md` (task closure, confirmation-gated)

| # | Question | Decision |
|---|---|---|
| 1 | **Matching** — how does the mechanism know which BACKLOG/ROADMAP line a session's work closes? | Structured commit-message trailer convention (e.g. `Closes: BACKLOG#<id>`), written by Claude Code as part of the commit that does the work. No natural-language inference at match time. |
| 2 | **Trigger** — when does the mechanism act? | Session-end, anchored to the session-start plan CONSTITUTION.md's Session protocol already mandates stating. Claude Code holds accumulated trailers through the session; at a point where completed work appears to satisfy the stated plan, it proactively asks the owner whether to close now or keep accumulating. No timer, no separate `/session-end` command. **"Natural completion point" resolved:** no text-matching heuristic infers plan completion. If Claude Code is not confident the stated plan is done, it asks directly — "Is the session's stated plan done, or not yet?" — rather than guessing from plan text or commit content. Same owner-confirmation gate as decisions 2/3, not a separate mechanism. |
| 3 | **Confirmation** — is there a human gate before a doc write? | Yes, mandatory, every time. No silent auto-write. The owner's explicit reply is what triggers the doc rewrite — answered as part of decision 2, not a separate mechanism. |
| 4 | **Ambiguous match** — more than one plausible closed item? | Present every plausible candidate and wait — nothing closes until the owner picks. Must be phrased in plain language for a non-technical reader: task titles as written in BACKLOG.md/ROADMAP.md (e.g. "This session's work might close either of these two tasks — which one, or both?"), never raw IDs or internal jargon alone. |
| 5 | **Blast radius / rollback** — if a wrong auto-close lands, what's the recovery path? | `docs/BACKLOG.md`/`docs/ROADMAP.md` are mutable working state, not a "publication" under Immutable Lineage. A wrong closure is fixed with an ordinary follow-up edit/commit; git history is the audit trail. Immutable Lineage stays scoped to ADRs/published artifacts as already defined. |
| 6 | **Recovery — owner never replies before the session ends** (resolved 2026-08-21, via `finding-unknowns` gap check) | Accepted as a real possibility, not designed away. No new log/document is created for this — explicit owner instruction. Trailers already persist in git commit history regardless of session state, so nothing is silently destroyed; it just waits to be found. See Mechanism design step 0. |

**Feasibility note.** Nothing in the above is infeasible as stated. The
"no wrong auto-write" risk that unconstrained natural-language matching
would create is closed structurally by decision 3 (mandatory confirmation
before every write) and decision 1 (structured trailer, not NL
inference) — not by claiming perfect matching accuracy.

## Design decisions — `docs/ARCHITECTURE.md`/`README.md` (structural fact-sync, direct-write)

Added 2026-08-21, second interview pass, after `finding-unknowns` found
the original SPEC understated its own scope (see Source below). Reasoned
through separately from the table above, not copy-pasted onto it — these
two files have different properties (already direct-write today, no
task-line-item structure).

| # | Question | Decision |
|---|---|---|
| A1 | **"Out of sync" meaning** — what does this mechanism's trigger actually check for these two files? | Structural fact-sync only: component/dependency lists, file paths, and similar fact-table content matching actual repo state — mechanically checkable by diffing against reality. Explicitly **not** narrative/prose accuracy (descriptive paragraphs about system behavior) — that would reintroduce natural-language judgment calls, the exact failure mode decision 1 above was designed to avoid. This mechanism can guarantee what it claims (verifiably diffable) rather than "probably accurate." |
| A2 | **Confirmation** — same mandatory gate as BACKLOG/ROADMAP, or different? | Same trailer-tagging + session-end batching pattern as decisions 1–2 above, but **no confirmation gate** — Claude Code writes directly at the same session-end checkpoint, consistent with the existing direct-write precedent (`apply_tier2_sync()`, ToolTempest ADR-0004) and `docs/CONSTITUTION.md`'s "unambiguous fact update, no confirmation needed" rule. Lower risk than BACKLOG/ROADMAP by design: A1's trigger is mechanically verifiable, not inferred from judgment about whether a task is "done." |

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

## Mechanism design — `docs/BACKLOG.md`/`docs/ROADMAP.md`

0. **Session-start recovery check** (new step, runs before step 1):
   before stating the new session's plan, Claude Code greps recent
   commit history for `Closes: BACKLOG#...`/`Closes: ROADMAP#...`
   trailers not yet reflected as closed in `docs/BACKLOG.md`/
   `docs/ROADMAP.md` — i.e. trailers left over from a prior session that
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
   completes (fully or partially) a specific BACKLOG/ROADMAP line, it
   adds a structured trailer to that commit's message. The trailer only
   tags the commit — no BACKLOG.md/ROADMAP.md edit happens at commit
   time.
3. Claude Code holds the set of accumulated trailers in session context.
4. **At a natural completion point** — when completed work appears to
   satisfy what the session's opening plan stated — Claude Code
   proactively asks the owner in plain language: "This looks like it
   completes the stated session plan. Update BACKLOG/ROADMAP now, or
   continue accumulating and batch it later?" When Claude Code is *not*
   confident the plan is complete, it does not guess from plan text or
   commit content — it asks directly instead: "Is the session's stated
   plan done, or not yet?"
5. **If the owner says continue:** Claude Code keeps holding the
   trailers and re-asks at the next natural completion point, rather
   than assuming.
6. **If the owner says close now:**
   - Exactly one candidate: Claude Code writes the BACKLOG.md/ROADMAP.md
     edit and commits/pushes it directly (the owner's own established
     direct-push path, ADR-0039 — no PR needed).
   - More than one plausible candidate: present all candidates in plain
     language (decision 4) and wait for the owner's pick before writing
     anything.
7. **If a closure later turns out wrong:** an ordinary follow-up
   edit/commit fixes it (decision 5) — no supersession ritual.

## Mechanism design — `docs/ARCHITECTURE.md`/`README.md`

Shares step 1's session-start and the session-end checkpoint (step 4)
with the BACKLOG/ROADMAP flow above — one checkpoint, not two unrelated
prompts. At that same moment, this flow runs silently alongside the
BACKLOG/ROADMAP prompt, not as a separate owner-facing interaction:

1. **During the session:** when Claude Code makes a commit that changes
   a structural fact tracked in `docs/ARCHITECTURE.md`/`README.md`
   (component list, dependency list, file paths — per decision A1), it
   tags that commit with its own structured trailer, distinct from the
   BACKLOG/ROADMAP trailer (exact key TBD, M1/M6 below).
2. Claude Code holds these trailers the same way it holds BACKLOG/
   ROADMAP trailers (step 3 above) — same session context, same
   accumulation.
3. **At the same session-end checkpoint** (step 4 above): Claude Code
   writes `docs/ARCHITECTURE.md`/`README.md` directly — no owner prompt,
   per decision A2 — using the existing `apply_tier2_sync()` write-safety
   infrastructure (snapshot before write, line-level diff, atomic apply,
   rollback on failure), not a new write path.
4. **If a write later turns out wrong:** an ordinary follow-up
   edit/commit fixes it, same as decision 5's rollback model — these
   files are equally mutable working state today, unchanged by this
   SPEC.

**Not resolved in this pass:** whether step 0's session-start recovery
check (BACKLOG/ROADMAP) has an equivalent for structural-fact trailers
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
  BACKLOG/ROADMAP flow deliberately adds a confirmation step narrower
  than that default (task-closure inference specifically, per decisions
  3/4); the ARCHITECTURE.md/README.md flow deliberately does *not* add
  one, staying consistent with that default (per decision A2).
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

- [ ] M1 — Define exact commit-trailer syntax for BACKLOG/ROADMAP closure
      (key name, ID format, full-vs-partial-progress distinction) and
      where Claude Code writes it in the commit message.
- [ ] M2 — Define the "work appears to satisfy the stated plan"
      matching heuristic operationally — what Claude Code actually
      checks before triggering the step-4 prompt.
- [ ] M3 — Plain-language candidate-presentation format for the
      ambiguous-match case (decision 4), reviewed against a
      non-technical-reader bar.
- [ ] M4 — Integration point in Claude Code's existing session/commit
      flow where steps 0, 2–6 hook in. Step 6's direct-commit path (the
      BACKLOG/ROADMAP closure write) must reuse `reconcile.py`'s existing,
      already-hardened `push_with_retry()` rather than an unguarded
      `git push` — same concurrent-push race class it was built to catch
      (this session's `finding-unknowns` Finding 3), same reuse-not-
      reinvent requirement as M7's `apply_tier2_sync()` reuse below.
- [ ] M5 — Test plan for the confirmation gate itself. Per
      `docs/CONSTITUTION.md`'s TDD section, this qualifies: "a
      confirmation/gating mechanism whose entire purpose is to trigger
      under specific conditions... 'does this actually trigger' is the
      central risk." Write a test defining the expected trigger/no-
      trigger cases before implementing, per that rule.
- [ ] M6 — Define the structural fact-sync trigger for ARCHITECTURE.md/
      README.md: exactly which facts are checked (component directory
      list, dependency list, file paths) and how they're diffed
      mechanically against actual repo state (decision A1).
- [ ] M7 — Integration with the existing, vendored `apply_tier2_sync()`
      (ToolTempest) — confirm the trailer-triggered write reuses that
      infrastructure rather than reimplementing snapshot/diff/rollback,
      and define the distinct trailer key from M1's BACKLOG/ROADMAP one.

Each milestone: status: not started. This session's task was explicitly
design-only — no implementation, no code, no other file, per the task's
own scope lock.

## Open questions / residual (not blocking, flag for the implementation session)

- Whether partial progress on a BACKLOG/ROADMAP item (not full closure)
  also gets a trailer and its own prompt, or whether this mechanism is
  full-closure-only — the interview's five decisions covered closure
  matching/triggering/confirmation but didn't explicitly address partial
  progress. Not decided here; don't assume either way without asking.
- Whether the session-start recovery check (step 0, BACKLOG/ROADMAP) has
  an equivalent for ARCHITECTURE.md/README.md structural-fact trailers
  orphaned by a session that ended before the session-end checkpoint
  fired — not decided in the second interview pass; flag before M7 is
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
