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

**Re-scoped during implementation (2026-08-20), then completed and
resynced (2026-08-21).** `TIER2_DOCS` lives in
`scripts/doc_sync_tier2.py`, `.gitignore`'d and vendored from the separate
`mikkiola/tooltempest` repository — not owned or committable here. Correctly
re-scoped as ToolTempest-side work; implemented there as ADR-0004,
commit `aaff388` ("feat(docops): add ADR-0004, README.md as 4th Tier 2
direct-write doc") — direct-write, not CODEOWNERS-gated, exactly the
design recorded in the BACKLOG pointer entry.

- [x] Landed in ToolTempest: `aaff388` (only reachable from ToolTempest's
      local `main` at the time; pushed to `origin/main` as part of this
      resync, since local and remote had one commit's worth of
      difference — a clean fast-forward, verified before pushing)
- [x] Resynced into article-pipeline: `.tooltempest.lock` repinned to
      `aaff38834ff3936eb3c4cbd2911615cfb9b5b47f`, `scripts/sync-tooling.sh`
      run. Verified, not just trusted: `TIER2_DOCS` now reads
      `("docs/ARCHITECTURE.md", "README.md", "docs/BACKLOG.md",
      "docs/ROADMAP.md")`; `GATED_DOCS` unaffected (still just
      `BACKLOG.md`/`ROADMAP.md`); byte-diff confirms the vendored
      `doc_sync.py`/`doc_sync_tier2.py`/`execution-record.schema.json`
      are identical to ToolTempest at `aaff388`;
      `scripts/test-sync-tooling-manifest.sh` passes (7/7 vendored
      files found); the pre-push hook's own ToolTempest-drift warning
      is now gone (pin matches `origin/main` exactly).
- [ ] Follow-up, article-pipeline-side, not yet done: update
      `CONTRIBUTING.md` to state README.md updates flow through the
      same contributor-supplied-content model as `ARCHITECTURE.md`
      (ADR-0034), now that `TIER2_DOCS` actually includes it.
- status: done (resync complete; the CONTRIBUTING.md follow-up remains
      open, tracked in `docs/BACKLOG.md`)

### M2 — Component-directory/doc pairing check extended to all four Tier 2 docs

**Correction (2026-08-21): the earlier re-scope to ToolTempest was
wrong, now reversed.** M2 was originally bundled with M1 under the same
"cross-repo, defer to ToolTempest" re-scope. That was incorrect: the
pairing check this milestone extends lives entirely in
`scripts/hooks/pre-push` (now `scripts/check-doc-pairing.sh`), an
article-pipeline-owned file, not `scripts/doc_sync.py`. Its
`component_dirs` list (`claim_extraction`, `evidence_package`,
`strategy_layer`, `author`, `quality_gate`, `platform_adapter`,
`experiment_log`) is article-pipeline's own project-specific knowledge
— ToolTempest's own README explicitly documents this as a deliberate
per-consumer boundary: "each consumer that wants it has to replicate
the pattern into its own pre-push hook independently." M1 (README.md →
`TIER2_DOCS`, genuinely generic) was correctly implemented in
ToolTempest (ADR-0004, commit `aaff388`); M2 should never have followed
it there.

Implemented here, in article-pipeline, extracted into its own script
(`scripts/check-doc-pairing.sh`) rather than left inline, so it's
independently testable: the existing ARCHITECTURE.md-only pairing check
now runs independently against all four Tier-2-tracked docs
(`docs/ARCHITECTURE.md`, `docs/BACKLOG.md`, `docs/ROADMAP.md`,
`README.md`), warning separately for each one a component-directory
change wasn't paired with — not a single combined "you missed one of
four" message.

- [x] Extended the pairing-check pattern from ARCHITECTURE.md-only to
      also cover BACKLOG.md, ROADMAP.md, and README.md
- [x] **Dependency, not re-decided here:** whether the pairing check
      stays warning-only or becomes hard-fail is still a separate, open
      `docs/BACKLOG.md` "Owner decisions needed" item — this milestone
      extends the check's *coverage* only; confirmed unchanged (still
      warning-only, exit 0 in every tested case, including all-four-
      missing)
- [x] Extracted into `scripts/check-doc-pairing.sh` (was inline in
      `scripts/hooks/pre-push`) — makes the check independently
      testable without needing gitleaks/doc_sync.py's own setup
- verify: a synthetic mutation test, same method as the gitleaks/ADR-
      citation gates. Done:
      `scripts/test-doc-pairing-check.sh` (permanent, committed) — four
      cases: no docs updated (all four warn), one doc updated (the
      other three warn, the updated one doesn't), all four updated (no
      warnings), no component change at all (no warnings). RED
      confirmed first against the pre-fix inline logic (a component
      change + ARCHITECTURE.md update produced zero warnings about the
      three missing docs — the exact gap this milestone closes); GREEN
      after the fix.
- done-when: mutation test confirms the check fires independently for
      all four docs, not just ARCHITECTURE.md. Met.
- status: done

- status: re-scoped, not implemented — see BACKLOG.md pointer

### M3 — ADR-0033 point 5: close and harden

- [x] Point 5 (close-and-reopen) confirmed moot — no reconciliation PR
      exists anywhere in the ADR-0035-narrowed design. Investigated this
      session (see Investigation Findings above).
- [x] A different concurrent-push race in `reconcile.py` confirmed real —
      investigated this session (see Investigation Findings above).
- [x] Hardened `reconcile.py`'s push step: `push_with_retry()` retries
      with fetch+rebase on non-fast-forward rejection (max 3 attempts),
      fails with a captured, logged error instead of an uncaught
      traceback if still rejected. TDD: scratch-repo race test written
      first, confirmed RED against the pre-fix script (uncaught
      `CalledProcessError`), then GREEN after the fix.
- [x] Recorded point 5 as closed/moot in `docs/BACKLOG.md` — an
      assessment closing, not a changed decision, so no new ADR was
      needed (nothing is being chosen differently than ADR-0035 already
      chose)
- verify: a simulated concurrent-run test (two `reconcile.py` invocations
      against the same stale local checkout, same method as the existing
      `index.lock`-contention finding's reproduction approach). Done: a
      scratch bare-repo setup with two clones, one pre-pushing a
      competing commit before the other's `reconcile.py` runs — RED
      (uncaught traceback) against the pre-fix script, GREEN (retry
      succeeds, both commits land on origin) after the fix, plus a
      separate permanent-failure case (broken remote) confirming a clean
      controlled exit 1, not a repeated crash.
- done-when: a rejected push no longer crashes uncaught; the evidence
      record for the retried/failed run is not silently lost in the
      common transient-race case (recovers via retry). A persistent
      failure (remote genuinely unreachable) still can't reach `origin`
      by definition — that case now fails loudly and cleanly instead of
      with a bare traceback, which is the achievable guarantee.
- status: done

### M4 — Audit implicit text-based contracts

Executes the action item already scoped in `docs/BACKLOG.md`'s
"P1 — Audit implicit text-based contracts" entry.

- [x] Ran the targeted grep audit across `scripts/doc_sync.py`,
      `scripts/doc_sync_tier2.py`, `.git/hooks/pre-commit`,
      `.git/hooks/pre-push` for text-matching-instead-of-structured-signal
      patterns. Full findings list recorded in `docs/BACKLOG.md`'s entry
      (now marked closed).
- [x] Listed findings read-only first — no fixes applied during the audit
- [x] Weighed each finding individually — every site classified as
      "not this failure class" (validates own doc content directly,
      exit-code/SHA/returncode-based, or git's own stable plumbing
      output) or "confirms an already-closed fix is solid on direct
      read"; one cross-reference noted (`verify.py`'s
      `resolve_component_name()`, a different script, already tracked
      as its own separate P1 item, not duplicated here)
- [x] Nothing required a fix this pass — no new unfixed instance found
- verify: the audit's own findings list, reviewed. Done: see
      `docs/BACKLOG.md`'s entry for the full classification.
- done-when: every text-matching site in scope is classified (fix now /
      defer / accept as-is) with a stated reason. Met: all sites
      classified "accept as-is" (not this failure class, or already
      fixed), with reasons stated per site.
- status: done (no TDD applicable — read-only audit, no new mechanism
      built, nothing whose triggering behavior needs a test)

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

- [x] Implemented the lightweight CI check
      (`scripts/check_adr_numbering.py` +
      `.github/workflows/adr-numbering-check.yml`): a new ADR's number
      doesn't collide with an existing one, and its header number
      matches its filename. TDD: RED against a synthetic scratch fixture
      (two files both claiming 0099, one file with a 0100/0101
      filename/header mismatch) confirmed nothing today catches this;
      implemented, then GREEN. First real-corpus run surfaced a genuine
      finding along the way: ADRs 0001–0031 use `# NNNN — Title` (no
      "ADR-" prefix) while 0032+ use `# ADR-NNNN: Title` — a real header-
      format difference, not a numbering bug; the check's regex was
      fixed to accept both without loosening the actual number-match
      invariant it enforces.
- [x] Wrote ADR-0036 (`docs/adr/0036-adr-lifecycle-state-machine-
      contract.md`) proposing the full lifecycle state machine
      (Proposed → Accepted → Deprecated/Superseded), an explicit
      Supersedes/Superseded-by field pair, and a generated
      `ADR-INDEX.md` — Accepted (the contract is decided), but
      explicitly scoped to the contract only: no CI enforcement, index
      generator, or field-pair check is implemented in this ADR or this
      milestone. Also records, as a Constraint, that the field pair
      doesn't model ADR-0035's point-level supersession case — flagged,
      not solved.
- verify: the lightweight check, mutation-tested against a synthetic
      number collision and a synthetic filename/header mismatch. Done:
      both violation types correctly detected and reported by message;
      real `docs/adr/` (36 files after ADR-0036) passes cleanly.
- done-when: both synthetic cases are caught; the proposing ADR exists
      and is Accepted or Rejected (implementation of its design is a
      separate, later task either way). Met: ADR-0036 is Accepted.
- status: done

### M6 — CHECKPOINT.md phase-out

Per owner decision: deprecate CHECKPOINT.md as a separate file. The
now-doubly-confirmed orphaning risk (this session's finding #2, plus the
priority-bug in Investigation Finding 2 above) is eliminated structurally
rather than managed with another lifecycle rule.

- [x] Investigated this session: confirmed `classify()`'s
      checkpoint-first priority means `CHECKPOINT.md`'s mere presence
      silently overrides any SPEC.md's own inline Milestones section
      (Investigation Finding 2 above)
- [x] Deleted root `CHECKPOINT.md` (`git rm`, the only one in the repo)
- [x] Modified `scripts/verify.py`'s `classify()` to drop the
      checkpoint-priority branch entirely (not just reorder it) — also
      removed the now-dead `validate_checkpoint_structure()` function
      and its two regex constants, and updated the module docstring and
      the UNKNOWN-case warning message accordingly. TDD: `classify()`
      tested in isolation against a scratch fixture (SPEC.md with
      well-formed inline Milestones + a CHECKPOINT.md present) —
      confirmed RED (`"checkpoint"`, silently ignoring the well-formed
      inline content) before the fix, GREEN (`"inline_spec"`, even with
      CHECKPOINT.md still present) after.
- [x] Recorded this as ADR-0037
      (`docs/adr/0037-checkpoint-md-pattern-deprecated.md`) — Accepted.
      Also resolves `docs/BACKLOG.md`'s "CHECKPOINT.md orphaning
      recurs" entry, whose own text left the decision open pending
      this outcome.
- verify: re-ran `scripts/verify.py` after `CHECKPOINT.md`'s deletion.
      Done: `pattern: "inline_spec"`, `source_file` is this SPEC.md
      itself, `structure.status: "OK"`, all units well-formed.
- done-when: `scripts/verify.py`'s own re-run confirms `"inline_spec"`
      discovery against this file, structurally OK. Met.
- status: done

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
