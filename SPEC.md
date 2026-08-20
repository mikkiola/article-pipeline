# DocOps — Consolidated Specification (Remaining Gaps)

## Overview

Designs the fixes for all currently-open DocOps-adjacent gaps in
`docs/BACKLOG.md`, consolidated into one pass per owner decision
(2026-08-20): README.md's missing mutation path, Tier 1's content-blind
validation, ADR-0033 point 5's status, the implicit-text-contract audit,
ADR lifecycle validation, and CHECKPOINT.md's lifecycle. Supersedes the
"separate `/spec` pass per item" plan from earlier this session — that
rule was meant for genuinely independent architectural decisions, not for
splitting one coherent documentation effort. The retrospective
mechanism-as-built spec committed as `dcb84e4` is unaffected; this SPEC.md
overwrites it at the single root location per `docs/CONSTITUTION.md`'s
SPEC.md rule, `dcb84e4`'s content stays recoverable via `git log -- SPEC.md`.

## Scope

**Glossary, broadened from `dcb84e4`.** "DocOps" here covers document-
governance automation generally, not only the 5-canonical-doc sync
mechanism: it also includes ADR lifecycle validation (`docs/adr/*.md`,
a different artifact class — ADRs aren't kept in sync with code, they're
immutable records, but their structural governance is adjacent DocOps
territory) and CHECKPOINT.md's lifecycle (not one of the 5 canonical docs,
but Tier 1's own direct validation target).

**Design constraint carried forward from ADR-0035.** Post-hoc gating
(confirming a mutation *after* it already landed) is the pattern ADR-0035
moved away from for BACKLOG.md/ROADMAP.md, for a documented reason (a
TOCTOU-adjacent structural no-op). Any new mechanism designed in this SPEC
that touches confirmation/gating (M1, M2) should not reintroduce that
pattern without a stated reason — checked below per milestone.

**Out of scope, unchanged:** everything not listed in the six items below
(numeric red-flag thresholds, contributor scoring/reputation, the
warning-only pre-push pairing check's own hard-fail decision — noted as a
dependency in M2, not resolved here).

## Investigation Findings (this session, first-hand)

Three factual claims verified directly, informing M3 and M6 below —
recorded here rather than only in a milestone, since they're evidence, not
design choices:

1. **`.github/CODEOWNERS`/`TIER2_DOCS` state, re-confirmed:** `TIER2_DOCS`
   is `("docs/ARCHITECTURE.md", "docs/BACKLOG.md", "docs/ROADMAP.md")`;
   `README.md` is absent from it and from `CODEOWNERS` — the gap M1
   closes.
2. **`scripts/verify.py`'s component discovery gives a paired
   `CHECKPOINT.md` unconditional priority over a SPEC.md's own inline
   Milestones section** — confirmed by reading its discovery logic:  a
   SPEC.md is classified as pattern `"checkpoint"` whenever a
   `CHECKPOINT.md` sits next to it, regardless of whether that SPEC.md
   also has a well-formed inline Milestones section. Consequence: the
   `dcb84e4` SPEC.md's own inline Milestones section was never actually
   structurally validated by Tier 1 — root `CHECKPOINT.md`'s mere
   presence silently redirected validation to it instead, the whole time.
   Repo-wide search confirms exactly one `CHECKPOINT.md` exists (root).
3. **`.github/scripts/reconcile.py`'s `git commit`/`git push` steps run
   with no retry or rejection handling** — confirmed by reading the
   script: the only `try`/`except` wraps the `apply_tier2_sync()` call;
   the commit and push calls after it are unguarded. Two contributor PRs
   merging close together could each trigger their own reconciliation
   run; if both attempt to push to `main` from stale local state, the
   second push is rejected (non-fast-forward) and crashes the script
   uncaught — losing that run's evidence record silently, since it was
   already written to disk but the commit containing it never reaches
   `origin`. This is a different mechanism than ADR-0033 point 5's
   original close-and-reopen (which was about a reconciliation PR going
   stale, not a git push race) — point 5 itself is confirmed moot (no
   reconciliation PR exists anywhere in the current, ADR-0035-narrowed
   design), but this is a live gap point 5's closure shouldn't paper over.
4. **`scripts/doc_sync_tier2.py` and `scripts/doc_sync.py` — M1 and M2's
   respective targets — are both `.gitignore`'d and vendored from the
   separate `mikkiola/tooltempest` repository**, confirmed via
   `git check-ignore -v` and a local ToolTempest checkout at
   `~/Dev/github.com/mikkiola/tooltempest`. Not caught when M1/M2 were
   originally scoped. Consequence: M1/M2 are re-scoped as ToolTempest-side
   work, filed as pointers in `docs/BACKLOG.md`, not implemented in this
   session — see M1/M2 below.

## Milestones

Six items below. M1/M2 re-scoped to `docs/BACKLOG.md` pointers during
implementation (Investigation Finding 4) — their design content stays
here, their checklist items don't, since there's nothing implementable
locally. M3–M6 carry ~13 checklist entries. Each states verify/done-when
per this project's CHECKPOINT.md field convention, now inline (see M6 —
this SPEC.md's own Milestones section is the first real exercise of the
inline pattern once `CHECKPOINT.md` is removed).

### M1 — README.md joins Tier 2 as a direct-write file

**Re-scoped during implementation (2026-08-20).** `TIER2_DOCS` lives in
`scripts/doc_sync_tier2.py`, `.gitignore`'d and vendored from the separate
`mikkiola/tooltempest` repository — not owned or committable here. This
milestone's actual work is ToolTempest-side; not implemented in this
session per owner decision. See `docs/BACKLOG.md`'s
"[TOOLTEMPEST] README.md → TIER2_DOCS" pointer entry for the deferred
design (still: Tier 2 direct-write, not CODEOWNERS-gated, consistent with
the ADR-0035 constraint above — that part of the design stands, only the
implementation location changed).

- status: re-scoped, not implemented — see BACKLOG.md pointer

### M2 — Tier 1 gains content-level doc-update checking

**Re-scoped during implementation (2026-08-20).** Same cross-repo issue as
M1: Tier 1's validation logic lives in `scripts/doc_sync.py`, vendored
from `mikkiola/tooltempest`, not owned here. Not implemented in this
session per owner decision. See `docs/BACKLOG.md`'s
"[TOOLTEMPEST] Tier 1 content-level doc-update checking" pointer entry for
the deferred design (extend the existing ARCHITECTURE.md-only pairing
check to all four Tier-2-tracked docs; the open warning-vs-hard-fail
dependency noted originally still applies unchanged).

- status: re-scoped, not implemented — see BACKLOG.md pointer

### M3 — ADR-0033 point 5: close and harden

- [x] Point 5 (close-and-reopen) confirmed moot — no reconciliation PR
      exists anywhere in the ADR-0035-narrowed design. Investigated this
      session (see Investigation Findings above).
- [x] A different concurrent-push race in `reconcile.py` confirmed real —
      investigated this session (see Investigation Findings above).
- [ ] Harden `reconcile.py`'s push step: retry with fetch+rebase on
      non-fast-forward rejection, or at minimum fail with a captured,
      logged error instead of an uncaught traceback that silently drops
      the evidence record
- [ ] Record point 5 as closed/moot in `docs/BACKLOG.md` — this is an
      assessment closing, not a changed decision, so no new ADR is needed
      (nothing is being chosen differently than ADR-0035 already chose)
- verify: a simulated concurrent-run test (two `reconcile.py` invocations
      against the same stale local checkout, same method as the existing
      `index.lock`-contention finding's reproduction approach)
- done-when: a rejected push no longer crashes uncaught; the evidence
      record for the retried/failed run is not silently lost
- status: not-started

### M4 — Audit implicit text-based contracts

Executes the action item already scoped in `docs/BACKLOG.md`'s
"P1 — Audit implicit text-based contracts" entry.

- [ ] Run the targeted grep audit across `scripts/doc_sync.py` and
      related hook scripts for text-matching-instead-of-structured-signal
      patterns (the same class as the two already-closed findings:
      staged-conflict git-flow inference, `verify_stderr` substring match)
- [ ] List findings read-only first — do not fix during the audit pass
- [ ] Weigh each finding individually (cost/likelihood of silent
      failure), same treatment as the already-closed finding #2 precedent
- [ ] Fix selectively per that weighing, not in bulk
- verify: the audit's own findings list, reviewed
- done-when: every text-matching site in scope is classified (fix now /
      defer / accept as-is) with a stated reason
- status: not-started

### M5 — ADR lifecycle validation

Two pieces per `docs/BACKLOG.md`'s own split: the lightweight check needs
no prior ADR and is included directly; the full state-machine design is
explicitly gated behind its own ADR per that entry's constraint. This
milestone's shape: implement the lightweight piece now, and scope the
full-design piece as *writing the proposing ADR only* — not prejudging
its content, not implementing ahead of its acceptance, but not skipping
the item either. Reasoning: this is the only shape that respects
"needs its own ADR before implementation" literally (no implementation
work is scoped here) while still giving the item real, boundable content.

- [ ] Implement the lightweight CI check: a new ADR's number doesn't
      collide with an existing one, and its header number matches its
      filename
- [ ] Write a new ADR (next free number at implementation time) proposing
      the full lifecycle state machine (Proposed → Accepted →
      Deprecated/Superseded), an explicit Supersedes/Superseded-by field
      pair, and a generated `ADR-INDEX.md` — proposal only
- verify: the lightweight check, mutation-tested against a synthetic
      number collision and a synthetic filename/header mismatch
- done-when: both synthetic cases are caught; the proposing ADR exists
      and is Accepted or Rejected (implementation of its design is a
      separate, later task either way)
- status: not-started

### M6 — CHECKPOINT.md phase-out

Per owner decision: deprecate CHECKPOINT.md as a separate file. The
now-doubly-confirmed orphaning risk (this session's finding #2, plus the
priority-bug in Investigation Finding 2 above) is eliminated structurally
rather than managed with another lifecycle rule.

- [x] Investigated this session: confirmed `classify()`'s
      checkpoint-first priority means `CHECKPOINT.md`'s mere presence
      silently overrides any SPEC.md's own inline Milestones section
      (Investigation Finding 2 above)
- [ ] Delete root `CHECKPOINT.md` (the only one in the repo, confirmed
      by repo-wide search this session) once this SPEC.md's own
      Milestones section is the authoritative tracking artifact
- [ ] Modify `scripts/verify.py`'s `classify()` to drop the
      checkpoint-priority branch, so future SPEC.md files are validated
      on their own inline content, not redirected to a stale paired file
- [ ] Record this as a new ADR (article-pipeline; deprecates the
      CHECKPOINT.md pattern `scripts/verify.py`'s own docstring
      currently documents as one of two valid mechanisms) — architectural
      change with sufficient basis (this interview's decision), per
      `docs/CONSTITUTION.md`'s autonomous-decision rule
- verify: re-run `scripts/verify.py` after `CHECKPOINT.md`'s deletion —
      this SPEC.md's own Milestones section must be discovered as
      pattern `"inline_spec"`, not `"UNKNOWN"`
- done-when: `scripts/verify.py`'s own re-run confirms `"inline_spec"`
      discovery against this file, structurally OK
- status: not-started

## Verification (Claim-Accuracy Checklist)

- [x] `TIER2_DOCS` is exactly the three pre-existing files; `README.md`
      is in neither `TIER2_DOCS` nor `CODEOWNERS`. Re-confirmed this
      session (see Investigation Finding 1).
- [x] `scripts/verify.py`'s `classify()` returns pattern `"checkpoint"`
      whenever a `CHECKPOINT.md` file exists next to a SPEC.md,
      unconditionally — read directly this session (Investigation
      Finding 2).
- [x] Exactly one `CHECKPOINT.md` exists in the repository (root).
      Verified: repo-wide filename search, this session.
- [x] `reconcile.py`'s `git commit`/`git push` calls have no
      surrounding `try`/`except` — only the `apply_tier2_sync()` call
      is guarded. Verified by reading the file directly, this session
      (Investigation Finding 3).

## Deferred / Not This SPEC

- The warning-vs-hard-fail decision for the pre-push pairing check
  (M2's stated dependency) — still an owner-only `docs/BACKLOG.md` item.
- Implementation of ADR lifecycle's full state-machine design — gated
  behind M5's proposing ADR being accepted first.
- Everything the retrospective `dcb84e4` spec already covers (the
  mechanism as built) — this SPEC only covers what's still open.

## Source

Architect-delegated task, this session, 2026-08-20, following a scope
correction after `dcb84e4` (single-item passes replaced with one
consolidated pass, per owner's reconsidered reading of the
independent-decisions rule). Pre-spec routing (phrase-decomposer +
finding-unknowns) ran fresh on this six-item consolidated scope before
the interview began: no BLOCKING cross-item conflicts found; two
glossary-scope notes (CHECKPOINT.md, ADR lifecycle) and one
design-constraint carryover (ADR-0035's anti-post-hoc-gate precedent)
were surfaced and incorporated into Scope above rather than blocking.
All investigation findings independently verified by direct file
reads/greps this session, not inherited from prior-session summaries.
