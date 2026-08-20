# Article Pipeline — Backlog

Two kinds of entries, kept separate: **Tasks** (a session can execute
these directly) and **Owner decisions needed** (only the project owner
can resolve these — a session should not guess a value or proceed past
one without an answer). Not a history log — see `docs/adr/` for
decided things. A task moves here from `docs/ROADMAP.md` when it's
concrete enough to execute; it leaves here when it's done or becomes
an ADR. An owner decision leaves here when the owner answers it — the
answer becomes an ADR if it's architectural, or gets applied directly
if it's a simple parameter.

P0 = blocks other work. P1 = should do soon. P2 = someday, not urgent.
Priority applies within each section separately — a P0 task and a P0
owner-decision block different things and don't compete with each
other for "which to do first."

Closed, not previously written here: the gitleaks false-negative on
Anthropic-key-shaped secrets, found during pre-push hook mutation
testing, tracked only verbally as a P1. Fixed in `cd796db`, confirmed
end-to-end (commit → hook → gitleaks → blocked push) via an isolated
mutation test on 2026-08-15 (temporary clone, not part of this repo's
history). No open item existed in this file to remove.

Also closed, not previously written here: the two remaining gaps from
a "Phase 14" methodology metacheck that a prior session started but
never finished or recorded anywhere (confirmed absent from all
commits, files, and ADRs by a dedicated audit on 2026-08-15). (1) The
pre-push hook's ADR-citation gate had never been mutation-tested —
only ever observed reporting "clean" on real, non-adversarial pushes.
Tested on 2026-08-15 using the same method as the gitleaks test above
(isolated clone, fake local bare remote, never touching real
`origin`): a deliberately introduced ADR-number citation, in the exact
backtick-wrapped four-digit format the hook's grep matches, appended
to a copy of `docs/ARCHITECTURE.md`, was confirmed to block the push
(non-zero exit, "failed to push some refs"), and a clean commit
afterward was confirmed to still push successfully. This closes the
gap — the gate is now demonstrated to actually catch a real violation,
not just report clean by default. (This paragraph itself avoids
writing that literal pattern, for the same reason.) (2) Whether the component-directory
/ ARCHITECTURE.md pairing check's warning-only design (it can never
block a push, by construction — see `.git/hooks/pre-push`) is
deliberate was investigated and found undocumented: no ADR, BACKLOG
entry, or commit message anywhere states a rationale for it. The
hook's own inline comment ("If nothing status-relevant changed... this
warning is safe to ignore") is the only related text on record, and it
does not establish whether the soft-only design is intentional or an
unaddressed gap. Not resolved — see "Owner decisions needed" below.

## Tasks

### P0

No open items remain — the isolated D-025 causal-question experiment
(the only P0 item) is done; see ADR-0031.

### P1

- [ ] Implement the English-first cascading search decided in
      ADR-0030: extend evidence_package/driver.py's
      QUERY_TRANSLATIONS_RU_EN table to cover treatment-query text and
      all future Claims (not just this pilot's 5), and wire the
      score-based cascade (English first, Russian fallback if score <
      2) into build_search_query()/run_searches(). Not started.
      Control-query translation table landed in commit 672a8d4 — cascade
      logic and treatment-query coverage still not implemented.
- [ ] Migrate Atom Selector and `graph_reader.py` from vendored copies
      into this repo as the single source of truth (currently
      duplicated with `brain.git`). Confirm after migration that
      exactly one of the two repos owns each file — not just that a
      duplicate was deleted.
- [ ] Rewrite `README.md` — it still describes an empty-scaffold state
      that hasn't been true since the first real component landed.
      This is the one-time catch-up fix for staleness that already
      exists; going forward, per `docs/CONSTITUTION.md`'s "Keeping
      documents current" rule, `README.md` updates directly as part of
      whatever task next makes its content stale — no separate
      BACKLOG item needed for that kind of drift after this one is
      done.
- [ ] Make the pre-push hook repo-tracked, not local-only. The hook
      just installed at `.git/hooks/pre-push` works, but `.git/hooks/`
      isn't tracked by git — it only exists on this machine. Tracking
      hooks via a committed `.githooks/` directory plus `git config
      core.hooksPath .githooks` (same pattern already proven in the
      Drift/`brain.git` project for a filename-length guard) would
      make the hook travel with the repo instead of disappearing on a
      fresh clone.
- [ ] Investigate atom tag quality / disambiguation: the D-025 paired
      experiment (context_layer/experiment_20260816_D025_paired.json,
      Claim `20260811T165911_03`) found a concrete failure mechanism —
      a tag ("доверие") that means interpersonal/epistemic trust in
      the atom's own sense got matched by search-query enrichment into
      an unrelated IT-security sense (trust certification standards,
      GOST/ISO 15408), causing a topic-drift regression (Δ = -1) in an
      otherwise-positive-leaning experiment. This suggests atom tag
      quality — specifically disambiguating polysemous tags — may be
      a contributing factor upstream of Claim Extraction and
      context_layer, not something either of those components can fix
      on their own. Not started; explicitly deferred until the D-025
      paired experiment (both language runs) is fully synthesized and
      closed as an ADR — not to be worked in parallel with it.
- [ ] Harness result classification currently conflates "verification
      failed" with "verification's prerequisite/environment was
      unavailable". Found in Step 4 of the automation track
      (scripts/harness.py, commit bd676b4): evidence_package-VC-001's
      verify_command chains `pip show linkup-sdk && bw get password
      ...` — when `pip` itself isn't on PATH, the command fails at
      exit 127 before `bw`/`BW_SESSION` is ever reached, and this gets
      recorded as plain FAIL, identical to how a real invariant
      violation would be recorded. A harness meant for unattended use
      needs to distinguish "the thing being checked is actually
      broken" from "a tool/session this check depends on isn't present
      in this environment" — otherwise a missing local dependency
      looks exactly like a real regression in any report or gate built
      on top of harness results. Not started; deliberately deferred
      out of Step 4 to avoid changing the harness result-class contract
      (currently PASS/FAIL/MANUAL/SKIPPED/UNKNOWN) mid-step. When
      picked up: grep every place `result`, `FAIL`, `SKIPPED`, and
      `UNKNOWN` are assigned or read across scripts/harness.py (and
      anything Step 6+ builds on top of it) before deciding whether a
      new PREREQ_MISSING class is warranted or whether an existing
      class can be repurposed with clearer semantics.
- [ ] `resolve_component_name()` (scripts/verify.py, Step 1 of the
      automation track) has a checkout-name dependency that silently
      degrades to a coin-flip on any clone not literally named
      `article-pipeline`. Found via a Step 7 mutation test
      (scripts/doc_impact.py, commit 2e3f982): the function's strong-
      signal match requires the literal string
      `f"{repo_root.name}/{component}/"` in a root-level SPEC.md's
      text — under a differently-named checkout this signal never
      fires, and the function falls back to a bare `"{component}/"`
      occurrence count, which produced a tied 4-4 count between
      `evidence_package` and `claim_extraction` and silently picked
      the wrong one. `ambiguous=True` IS set correctly in this case
      (verify.py already warns), but the wrong component name still
      propagates forward into everything built on top of it (Steps
      3-7's checklist/harness/drift/doc-impact outputs), where the
      warning is easy to miss in a large stdout stream. This would
      affect CI or any second clone/worktree today, not just a
      hypothetical. Not started. When picked up: either make the
      strong-signal match independent of the actual checkout directory
      name (e.g. match any `<dir>/<component>/` pattern rather than
      requiring the real root dir's literal name), or have downstream
      consumers (checklist.py, doc_impact.py, etc.) treat
      ambiguous=True as a hard stop rather than a warning to carry
      forward silently — needs a decision, not just a patch, since
      changing ambiguous-handling downstream affects multiple already-
      committed scripts.

### P2

- [ ] Design a support-type classification for Evidence's `verified`
      status (mechanism-supported / outcome-supported /
      semantic-supported / unsupported) instead of the current binary
      criterion. Don't start until the P0 context-layer task above is
      done — changing both at once makes it impossible to tell which
      fix caused which effect.
- [ ] Implement an Article Pipeline-side adapter against ToolTempest's
      existing CLI/discovery contract (see `docs/adr/`) — this project
      consumes that contract, it doesn't own or extend ToolTempest
      itself. Manual sync works today; this replaces it with
      automatic-detection + explicit-install.
- [ ] Translate the three remaining Russian-language files in
      `claim_extraction/` to English.
- [ ] Add a second search API backend (Exa) as an alternative to
      Linkup — interface already supports swapping backends, nothing
      built. Value depends on how stable Evidence Package's interface
      is after the P0 context-layer fix — low priority until then.
- [ ] Fix one immutable pilot log line that contains a personal
      filesystem path — do this only when the repo goes public, not
      before. This is not a same-artifact edit (that would break the
      append-only guarantee) — it needs either a superseding
      append-only record or a separate mechanism, decided at the time.
- [ ] Add an explicit schema check (or a test) confirming Evidence
      records always carry `source_url` and `license`, even when
      null — the invariant `docs/adr/0023` states. A mutation test
      (2026-08-14) found no independent check: the invariant currently
      holds only because `build_evidence_run`
      (`evidence_package/write_evidence.py`) accesses these fields via
      dict subscript (`item["source_url"]`), which happens to raise
      `KeyError` on a missing input field rather than silently
      omitting it from the output record. A future refactor to
      `.get()`, or any code path that writes an Evidence record
      without going through this function, would silently break the
      invariant with nothing in the codebase to catch it — no test
      suite exists anywhere in this repo.
- [ ] Add mechanical detection/prevention of modifications to accepted
      ADR files in docs/adr/ — the rule "an accepted ADR is never
      edited after acceptance" exists in docs/CONSTITUTION.md, but
      nothing currently checks for a violation of it. No design
      proposed yet — this item is registration of the gap, not a
      solution.
- [ ] Evidence Package re-run comparisons (old run vs. new run) have
      never isolated assessment-pass quality as a variable. A second
      interactive assessment pass can independently change a Claim's
      status regardless of whether the search query changed at all —
      surfaced by a direct audit of the context-layer re-run experiment
      above, where the one observed status change was traced to a
      reassessment effect, not the query change under test. No
      experiment run in this project so far has controlled for this.
      No design proposed yet — this item is registration of the gap,
      not a solution.

## Owner decisions needed

These are not tasks — no session should invent a value for these or
proceed past one silently. Each becomes an ADR once answered, if the
answer has architectural consequences.

- Numeric red-flag thresholds for Phase 1 (minimum % of atoms with a
  usable Claim, etc.) — not yet set.
- Minimum number of stable days on Habr+LinkedIn before adding a third
  platform — not yet set.
- Confidence-threshold mechanism (configurable numeric threshold) vs.
  the interactive assessment actually used in the Claim Extraction
  pilot — possibly the same mechanism described twice, or two
  separate layers. Not technically verified either way; needs a
  decision on whether this is worth resolving now or deferring.
- Is the pre-push hook's component-directory/ARCHITECTURE.md pairing
  check meant to stay warning-only (never blocking a push)
  permanently, or was that a gap left from initial implementation that
  should eventually become a hard fail? No rationale for the current
  design is on record anywhere (checked: the hook itself, `docs/adr/`,
  `docs/BACKLOG.md`, commit messages). A hard fail would also need to
  handle the false-positive risk on legitimate non-architectural
  changes the hook's own inline comment already acknowledges (e.g. a
  bugfix to a component directory that doesn't change its
  Status/Validation/Commit).

### P1 — Audit implicit text-based contracts in the DocOps protocol

Pattern, not a one-off finding. Twice in the DocOps Protocol, one
component has inferred another component's state from an unstructured
text signal instead of an explicit code or field:

1. Staged-conflict bug (ToolTempest, commit c25dd72). RECONCILE
   inferred git-flow intent from the fact that a file was staged,
   without checking for a staged/unstaged divergence. Found only
   through a live test, not a code review.
2. verify.py substring match (found 2026-08-19, DocOps V2.0 hardening
   session). doc_sync.py determined "nothing to check" by testing
   `"no SPEC.md files found" in verify_stderr`. Fixed by introducing
   exit codes 0/1/2: article-pipeline commit `c8641cd7e84624a3ca03d7927d7872ab654a3cd1`
   (scripts/verify.py:276, `return 1` → `return 2`) and tooltempest
   commit `b66de81f9011ccd5e957a93ece15a77edc872881`
   (scripts/doc_sync.py:304, substring match → `exit_code == 2`). Both
   commit messages name the accepted risk explicitly: external callers
   of verify.py outside this repository, invisible to a grep search,
   that currently treat exit 1 as "nothing to check" will break
   silently. Regression-tested: HARD BLOCK on a MALFORMED file still
   returns exit 1; the no-SPEC.md case now cleanly returns exit 0.

Root cause, not coincidence. Any point in the protocol where component
A infers component B's state from text (stderr content, git diff
heuristics, string comparison) rather than a structured signal (exit
code, JSON field, explicit API) is a candidate for a future silent
failure. Both findings above belong to this same class.

- [ ] Action item: before ToolTempest gains a second consumer
      (deliberately out of scope for now — this is not readiness for
      replication), run a targeted grep audit of scripts/doc_sync.py
      and related hook scripts for any other place where parsing
      depends on text matching instead of a structured signal. Do not
      fix everything at once — list findings read-only first, weigh
      each one individually (as was done for finding #2 above), and
      fix selectively, not in bulk. Not started.

Out of scope for this item: re-testing the already-fixed staged-
conflict and substring-match cases — both are closed separately.

### Resolved — .tooltempest.lock resync (closed)

article-pipeline/.tooltempest.lock was pinned at c25dd72 (pre-fix) when
the substring-match fix above landed in ToolTempest. Resynced via
scripts/sync-tooling.sh, then the pin itself committed: article-pipeline
commit `f681e59774471f5a2291478217f1fe1d815aaac1` ("fix(docops): repin
.tooltempest.lock to tooltempest@b66de81").

Verified independently, not just by trusting script output: hash and
byte-diff of the vendored scripts/doc_sync.py and
schemas/execution-record.schema.json (both gitignored — vendoring
split by design, not a diff-scope gap) confirmed the on-disk content
matches ToolTempest b66de81 exactly. The no-op and HARD BLOCK checks
were re-run against the synced article-pipeline copy specifically —
both matched the results already confirmed directly against
ToolTempest, no divergence.

ToolTempest's `main` also needed a push (b66de81 existed only in the
local checkout; origin/main was still at 31f48b7) — confirmed and
approved before pushing, since publishing to a shared remote is a
visible action, not push straight from a routine sync.

Source. DocOps Protocol V2.0 hardening session, 2026-08-19. Finding #2
from Claude Code's read-only comparison of ADR-0001 against
scripts/doc_sync.py, plus systems-loop analysis (O'Connor lens) in the
architect chat.

### P2 — doc_sync.py STAGE step can raise an unhandled exception on index.lock contention

Found during the 2026-08-19 edge-case audit (Scenario 4b, ToolTempest
scripts/doc_sync.py). The STAGE step's `git add` call
(`subprocess.run(["git", "add", *git_add_paths], cwd=root, check=True)`)
has no try/except, unlike every other failure path in the file, which
prints a `[doc_sync pre-commit] FAIL: ...` message and does a clean
`return 1`. If it collides with another process holding
`.git/index.lock`, `check=True` raises `subprocess.CalledProcessError`
unhandled — a raw Python traceback surfaces to the user instead of the
file's otherwise-consistent clean-FAIL pattern.

Reproduction note, important for triage: this was only reproduced by
bypassing git's own commit-time serialization — two `doc_sync.py
pre-commit` processes launched directly and concurrently against the
same staged state, not two real sequential `git commit`s. Two real,
back-to-back commits were also tested in the same session and did not
race (git's own `.git/index.lock` serializes them, so the hook never
actually runs twice at once under normal usage — one `doc_sync.py`
invocation per real `git commit`).

- [ ] Harden the STAGE step's `git add` call against `index.lock`
      contention (or otherwise decide it's out of scope, since normal
      hook usage doesn't trigger it) — not started. Classified P2, not
      P1: narrow, requires an abnormal invocation pattern to surface,
      not something normal single-commit-at-a-time hook usage hits.
      Filing only; no fix implemented as part of this entry.

Source. DocOps Protocol V2.0 hardening session, 2026-08-19 edge-case
audit (Scenario 4b) in the architect chat.

### P1 — [TOOLTEMPEST] CI for ToolTempest, before the second consumer connects

<!--
  FILED HERE, NOT IN TOOLTEMPEST: this task is about ToolTempest's own
  infrastructure (CI for the shared tool), not about article-pipeline.
  It's filed in article-pipeline's docs/BACKLOG.md anyway, as a
  deliberate exception, not an architectural default — ToolTempest
  doesn't have an established backlog/issue-tracking convention of its
  own yet, and the owner explicitly chose "filed somewhere I'll
  actually see it again" over "filed in the technically correct repo
  but likely to be forgotten." The [TOOLTEMPEST] tag exists so this
  entry is never mistaken for an article-pipeline task — when picked
  up, the actual work (CI config, pipeline) happens in the tooltempest
  repository, this entry is a pointer, not the task's home.
-->

**Why now, not "someday."** ToolTempest currently has one consumer
(article-pipeline). A second and third consumer are realistically
expected within the next few months (per the owner's own roadmap
timeline, 2026-08-19 session), with up to eight eventually. Every fix
landed in ToolTempest today only reaches consumers via a manual,
easy-to-forget resync step — this session alone hit that exact gap
three separate times (the verify.py exit-code fix, ADR-0002's push,
and the UNKNOWN-pattern fix), each caught only because the architect
or Claude Code happened to notice, not because anything enforced it.
With one consumer, a missed resync or a bad fix is inconvenient. With
several, the same gap becomes silent divergence across projects — some
running a fixed version, some not, with no visibility into which is
which.

**What's needed, concretely.** A CI pipeline in ToolTempest itself
(most likely GitHub Actions, given the repo already lives on GitHub)
that automatically runs the pre-commit/pre-push scenario suite already
exercised manually in this session — no-op, ordinary RECONCILE,
genuine staged/unstaged conflict HARD BLOCK, detached HEAD, no
upstream, UNKNOWN-pattern touched/untouched, verify.py missing/broken
— on every commit to main, before it's mergeable. This catches a bad
fix at the source, before any consumer can pull it, rather than
relying on manual scratch-repo testing being repeated correctly every
single time a change lands.

**Not required alongside CI, but worth deciding together when this is
scoped:** whether resync should also become semi-automatic (e.g., a
bot that opens a PR in each consumer repo when origin/main advances,
requiring one approval click rather than a fully manual
scripts/sync-tooling.sh invocation each time) — this closes the "we
forgot" gap without removing the human review step, unlike full
auto-resync, which would propagate a bad fix instantly to every
consumer with no pause. Worth a real decision when this is picked up,
not assumed either way here.

**Drift Warning mechanism — decided (2026-08-19).** The check runs at
pre-push, not pre-commit. Rationale: pre-commit fires often and must
stay instant and offline-safe (no network call should be added to the
most frequent, most latency-sensitive git operation). pre-push is the
point where network access is already guaranteed -- the author is
about to send data to GitHub regardless, so checking whether
origin/main in tooltempest has advanced past the local
.tooltempest.lock pin adds no new network dependency, only reuses the
connection the push itself requires. The warning surfaces slightly
later than a commit-time check would (at push, not at the moment of
the local commit), which is an accepted, deliberate trade-off, not a
gap -- push is also the natural moment to notice drift, since it's
when the author is about to share this state externally anyway. Not
yet implemented; scoping happens alongside CI.

**Not this session's scope.** Sizing, choosing the CI platform, and
writing the actual pipeline config are a dedicated task, not something
to bundle into DocOps V2.0 hardening. Flagging with a concrete timing
rationale so it isn't lost as abstract "someday" backlog noise.

**Source.** DocOps Protocol V2.0 hardening session, 2026-08-19 —
raised after the third resync-gap instance in one session, discussed
in the architect chat regarding solo-developer risk tolerance for
propagating a shared-tooling fix (e.g., a Python version bump breaking
the recipe for every connected project).

### P2 — doc_sync_tier2.py CLI exit-code semantics for no-op runs

Found during Tier 2 Stage 4 (CLI entry point) implementation,
2026-08-19. `apply_tier2_sync()`'s CLI wrapper exits 0 only when
`result["status"] == "applied"`; a fully valid invocation where the
proposed content matches what's already on disk (`status ==
"no_changes"`) exits non-zero, per the literal Stage 4 task wording
("0 if applied, non-zero otherwise"). A future scripted/CI caller
treating any non-zero exit as a hard failure would conflate "nothing
needed to change" with a real error (bad JSON, a gated-document
rejection, etc.).

- [ ] Not fixed now: no automated caller exists yet to be affected by
      it. Revisit when Phase 5 (sync-tooling completeness, below) or
      ADR-0033's GitHub Actions implementation gives this a real
      caller.

**Source.** Tier 2 /doc-sync implementation session, 2026-08-19,
Stage 4.

### P2 — ADR lifecycle state machine + structural validation + generated index

Found during the ADR-0033 discussion (contributor governance),
2026-08-19. Currently ADR status is free-text and unenforced: there is
no automated check that a new ADR's number is unique, that a
"Supersedes" relationship is followed through (the old ADR actually
marked Superseded), or that status transitions are valid. Not urgent
while the project has one contributor, but becomes relevant once
ADR-0033's contributor flow is live and external PRs can introduce
ADRs.

Two separable pieces, do not conflate:

- [ ] Lightweight: a CI check that a new ADR's number doesn't collide
      with an existing one and that the file's header number matches
      its filename.
- [ ] Full design (explicitly deferred — needs its own ADR before
      implementation, per the external review discussed this session):
      Proposed → Accepted → Deprecated/Superseded as an enforced state
      machine, an explicit "Supersedes"/"Superseded by" field pair
      checked by CI, and a generated `ADR-INDEX.md` as a derived
      artifact (not hand-maintained). Do not implement this piece
      without a preceding ADR describing the lifecycle contract itself
      — decided this session, per the discussion of Log4brains/
      MADR-style tooling as prior art.

**Source.** Tier 2 /doc-sync implementation session, 2026-08-19,
ADR-0033 discussion.

### P1 — sync-tooling.sh completeness testing (Phase 5)

Found during the Tier 2 implementation session, 2026-08-19.
`.tooltempest.lock` was repinned to a new ToolTempest commit that
included a new file (`scripts/doc_sync_tier2.py`), but
`sync-tooling.sh`'s vendored-file list is a static, hand-maintained
list written before Tier 2 existed. The repin succeeded (correct SHA
pinned, Drift Warning silenced) while the new file silently failed to
reach article-pipeline — caught only because Claude Code manually
diffed the two ToolTempest commits during an unrelated task, not by
any automated check. Fixed for this specific case (see commit
`f51c528`), but the underlying gap — no test catches a new ToolTempest
file that should be vendored but isn't — remains.

Two separable pieces, do not conflate:

- [x] Regression test (cheap): verify every file currently listed in
      `sync-tooling.sh`'s copy commands actually exists in ToolTempest
      at the pinned commit. Catches typos/renames/deletions in the
      existing list, not missing new entries. Implemented as
      `scripts/test-sync-tooling-manifest.sh`, 2026-08-19: parses the
      `cp` lines out of `sync-tooling.sh`, resolves the pinned commit
      from `.tooltempest.lock`, and checks each vendored path's
      existence in the ToolTempest repo at that commit via `git
      cat-file -e`. Passes against current state (7/7 files found);
      failure path confirmed with a synthetic missing-file case
      (non-zero exit, names the missing file).
- [ ] Completeness design (architectural, needs its own decision —
      likely its own ADR, ToolTempest-side, since it changes what
      ToolTempest commits to exposing to consumers): how a consumer
      discovers that a new ToolTempest file should be vendored,
      without hand-maintaining a list. Candidate direction discussed: a
      manifest file living in ToolTempest itself, with
      `sync-tooling.sh` reading from it instead of hardcoding paths.
      Decided — see below.

**Decision (owner, 2026-08-19).** Option A — a manifest file living in
ToolTempest, which `sync-tooling.sh` reads instead of hardcoding
paths. Chosen over a ToolTempest-side CI check (Option B) because B
has a hard dependency on CI infrastructure that doesn't exist yet (see
the separate "[TOOLTEMPEST] CI... before the second consumer connects"
item) — A has no such dependency and can proceed now. B remains a
valid future addition on top of A once CI exists (see the new
"Email notification on vendoring drift" item below), not a competing
alternative.

Implementation of Option A itself is NOT scoped by this decision —
this entry's own text already notes it "changes what ToolTempest
commits to exposing to consumers," likely needs its own ADR,
ToolTempest-side. This records the decision; a future task scopes and
implements it.

Sequencing: after current Tier 2 work closes (Tier 1 regression check
+ final doc-sync marking Tier 2 as implemented).

**Source.** Tier 2 /doc-sync implementation session, 2026-08-19.

### P1 — Implement ADR-0033's GitHub Actions workflow

Found: 2026-08-19. ADR-0033
(docs/adr/0033-contributor-governance-post-merge-reconciliation.md) is
Accepted — the design for a contributor-facing GitHub Actions workflow
is fully specified, including token scoping, the
reconciliation-PR-as-confirmation mechanism, and the close-and-reopen
resolution for concurrent `docs/` changes. The workflow itself has not
been built. Acceptance of the ADR was mistakenly treated as equivalent
to this being scheduled work in an earlier draft of a session handoff
document — it wasn't; this entry corrects that gap.

Scope of the implementation task (per ADR-0033's own Decision and
Validation sections, do not re-derive):

- [x] GitHub Actions workflow calling `apply_tier2_sync()` for
      `ARCHITECTURE.md` (ADR-0033 point 1, narrowed — see ADR-0035
      below: no gated-doc diff-capture half of this step remains,
      since there is no longer a reconciliation PR to feed it). Done:
      `.github/workflows/adr-0033-reconciliation.yml` +
      `.github/scripts/reconcile.py`, 2026-08-20. Verified by dry-run
      against an isolated scratch repo (fake local origin, no real
      GitHub/network side effects) — `no_changes` path (content
      already matches, the common case), the file-absent edge case,
      and a real `git commit`+push-to-fake-origin all confirmed
      working end-to-end. NOT tested against a real GitHub
      `pull_request: closed` event — that's the separate testing
      checkbox below. One finding from the dry-run: `status: "applied"`
      is structurally unreachable in this design, not just untested —
      `proposed` is always read from the same on-disk content
      `apply_tier2_sync()`'s own internal snapshot also reads, so the
      diff is always empty by construction. Only `no_changes`/`error`
      are reachable outcomes; noted, not fixed here (would require
      diffing against pre-merge git history, deliberately kept out of
      this narrowed slice's scope).
- ~~Reconciliation PR opened for `BACKLOG.md`/`ROADMAP.md` changes;
      merge = accept, close-without-merge = reject (point 2).~~
      **Superseded by ADR-0035** — see decision note below. Not
      implemented; will not be, under the current design.
- ~~Rollback on PR close triggers `restore_snapshots()` via a
      GitHub event handler (point 3).~~ **Superseded by ADR-0035** —
      no post-merge gated-doc mutation exists to roll back. Not
      implemented; will not be, under the current design.
- [x] Scope-zeroed, least-privilege token permissions per job — no job
      scoped to merge authority (point 4, simplified per ADR-0035's
      Consequences: no reconciliation-PR-opening job, no PR-close
      rollback job — only the point-1 `ARCHITECTURE.md`-write job
      needs a permissions block now). Done: top-level `permissions: {}`
      plus `permissions: {contents: write}` on the single `reconcile`
      job only — no `pull-requests` scope anywhere in the workflow.
- [ ] Close-and-reopen handling for concurrent `docs/`-touching merges
      (point 5) — status re: ADR-0035 not yet assessed; point 5 was
      written for the now-superseded reconciliation-PR flow, may need
      re-scoping once point 2/3 work is dropped.
- [x] Evidence logging matching Tier 1's existing record format
      (point 6). Done, adapted: `reconcile.py` writes one JSON record
      per run to `.tempest/runs/`, reusing Tier 1's naming
      (`make_run_id()`) and retention (`prune_run_records()`)
      convention — but NOT `schemas/execution-record.schema.json`
      itself, which was found (by reading it) to be pre-commit-only
      (`hook` enum literally `["pre-commit"]`, `additionalProperties:
      false`, fields specific to CHECKPOINT.md/SPEC.md structural
      counters). Reusing that schema verbatim for a reconciliation run
      isn't possible without violating its own constraints. The
      record instead carries `pr_number`, `merged_commit_sha`,
      `written`, `status` (`applied`/`no_changes`/`error` — narrowed
      from ADR-0033 point 6's original `applied`/
      `rejected-and-rolled-back`/`superseded-by-reopen`, since the
      latter two belonged to the now-superseded reconciliation-PR
      flow), and `error`. Verified by dry-run (see point 1's note
      above) that the record is written, correctly shaped, and
      committed alongside (or in place of) the `ARCHITECTURE.md`
      write.
- [ ] Testing per ADR-0033's Validation section — GitHub-event-adapted
      equivalents of Tier 2 Stage 3's scenarios, plus the
      close-and-reopen path under a simulated concurrent merge. Scope
      narrows with points 2/3's removal; not re-derived here.
- [ ] Manual follow-up, not a code task: configure GitHub branch
      protection on `main` to require code-owner review on
      `docs/BACKLOG.md`/`docs/ROADMAP.md` (the `.github/CODEOWNERS`
      file alone has no enforcement effect until this is turned on —
      per ADR-0035's Validation section).

**Status correction (2026-08-19).** No `.github/workflows/` file
exists yet — confirmed via `find .github`, `git log --all -- .github/`,
and `git status`, all empty. A "first slice" implementation of point 1
was attempted this session but stopped at a BLOCKING finding-unknowns
result (the `proposed`-content-source gap, since resolved — see
ADR-0034 and `CONTRIBUTING.md` below) before any file was created.
Resolving that blocker did not retroactively build the skeleton; none
of the checkboxes above should be read as started. A later task
attempting to "extend" or build on an existing workflow file should
first re-confirm this file still doesn't exist, rather than assuming
a prior session completed it.

**Decision (owner, 2026-08-19).** The content passed as `proposed` to
`apply_tier2_sync()` is supplied by the contributor — their own PR
includes the doc updates (`ARCHITECTURE.md`/`BACKLOG.md`/`ROADMAP.md`)
per a documented contribution requirement (see the new
`CONTRIBUTING.md` item below), not generated by the Action or an LLM
call inside it. The Action re-reads the merged PR's tree rather than
generating content. This resolves the BLOCKING gap found this
session: ADR-0033's own text specifies the confirmation/atomicity/
rollback mechanics but never states where `proposed`'s content
originates — this was an unstated assumption in the accepted ADR, not
a decided detail.

This decision changes what ADR-0033 point 1 means in practice: for
`ARCHITECTURE.md`, `apply_tier2_sync()`'s "direct write" becomes an
effective re-write of content the contributor's merge already
committed to the tree, not new content generation. This is a material
enough clarification of an accepted ADR's unstated premise that it
should be recorded as its own ADR (new number, article-pipeline,
references and extends ADR-0033, does not edit it per Immutable
Lineage) before the workflow implementation resumes — filed as the
first checkbox below.

Rejected alternatives (investigated this session, not chosen): an LLM
call inside the Action drafting doc updates from the PR diff (new
dependency, cost, and failure surface on the project's most protected
documents); a revived rule-based diff classifier (`doc_impact.py`-
style — already built and explicitly abandoned in this repo, commit
`a8487c4`, as "too conservative, wrong scope"); the owner manually
supplying `proposed` per PR (adds a manual step this decision avoids).

- [x] Write a new ADR (article-pipeline, next free number per `ls
      docs/adr/`) documenting this decision before resuming Part B's
      GitHub Actions workflow implementation. Done: ADR-0034
      (`docs/adr/0034-contributor-supplied-doc-updates.md`),
      2026-08-19.
- [x] Add a `CONTRIBUTING.md` requirement (new or existing file, check
      first) stating that a PR touching functionality requiring
      `ARCHITECTURE.md`/`BACKLOG.md`/`ROADMAP.md` updates must include
      those doc updates in the same PR, in the format Tier 1/Tier 2
      doc-sync expects. Done: `CONTRIBUTING.md` created (new file),
      2026-08-19.
- [ ] Confirm what Tier 1's existing pre-commit/pre-push doc_sync
      validation actually checks today — whether it already flags a
      PR missing required doc updates, or whether that's a gap this
      decision now depends on closing. Do not assume either way; check
      `scripts/doc_sync.py`'s actual logic.

**Finding (2026-08-19).** Tier 1's `doc_sync.py` does NOT cover this —
confirmed gap, not covered. Read in full: `cmd_pre_commit()` and
`cmd_pre_push()` both operate entirely through `run_verify()`
(`scripts/verify.py`), which discovers and structurally validates only
per-component `SPEC.md`/`CHECKPOINT.md` files (required-field
presence, milestone-checkbox structure) — it contains no logic that
inspects `ARCHITECTURE.md`, `BACKLOG.md`, or `ROADMAP.md` at all, and
no logic that checks whether a commit/PR touching functionality
requiring doc updates actually included them. `pre-commit`'s own
success message ("N doc-owned file(s) scanned, all structurally OK")
is accurate: it is a structural check of files already present, not a
completeness check of whether the right files are present.

The one place `ARCHITECTURE.md` is examined at all is a separate
mechanism, not part of `doc_sync.py`: `scripts/hooks/pre-push`'s own
inline "component-directory changes paired with an ARCHITECTURE.md
update" check. It is warning-only (never sets `fail=1`, never blocks
a push — confirmed by reading the script), checks `ARCHITECTURE.md`
only (never `BACKLOG.md`/`ROADMAP.md`), and only fires for a
hardcoded list of component directories. This check, and whether its
warning-only design is deliberate, is already a separate, open item
in this file's "Owner decisions needed" section — not resolved here.

ADR-0034's Consequences section correctly flagged this as an open,
unverified dependency. This confirms it as a real gap; no fix is
proposed here — a future task scopes one.

**Decision (owner, 2026-08-19).** ADR-0033 points 2 and 3 (the
post-merge reconciliation PR as confirmation gate for
`BACKLOG.md`/`ROADMAP.md`, and rollback on its rejection) are
superseded by ADR-0035
(`docs/adr/0035-pre-merge-gate-for-gated-docs.md`). Found this
session, Part B second slice: building the workflow revealed that
under ADR-0034 (contributor supplies gated-doc content in their own
PR, which merges normally before any post-merge automation runs), a
reconciliation PR computed against current `main` always has an empty
diff — the content it would propose already matches what's on `main`,
since the contributor's ordinary merge already wrote it. This makes
points 2/3 a structural no-op, not a fixable implementation detail —
a finding-unknowns BLOCKING result, reported and stopped on before
any workflow code was written. Three independent external
architectural reviews this session converged on the same diagnosis
(gate-after-mutation / post-hoc gate / TOCTOU-adjacent pipeline
conflict) and the same fix: a pre-merge gate via GitHub CODEOWNERS +
branch protection on the two gated paths, replacing the post-merge
reconciliation-PR mechanism entirely for those files. ADR-0033 itself
is unedited (Immutable Lineage); points 1, 4, 5, 6 remain in effect,
point 4 simplified per ADR-0035's Consequences. `.github/CODEOWNERS`
is added as part of this decision; branch protection configuration
itself is a manual GitHub repo-settings step, not done as part of
this decision — see the checkbox above.

### P2 — Email notification on vendoring drift (depends on [TOOLTEMPEST] CI)

Found: 2026-08-19, during the sync-tooling.sh completeness (Phase 5)
piece-2 decision. The owner wants to be notified by email if a
vendoring drift or CI failure occurs while not actively working the
project (e.g., away on another project) — a silent local script
failure isn't enough. This is not a competing mechanism to the
manifest decision (Option A, above) or a future CI check (Option B)
— it's a notification channel layered on top of whichever detection
mechanism exists.

Hard dependency: cannot be implemented before the "[TOOLTEMPEST] CI,
before the second consumer connects" item exists and runs, since
there is no CI job to attach a failure notification to yet. GitHub
Actions supports failure-triggered email natively via repository
notification settings once a workflow exists — no custom code is
expected to be needed for the basic case, but this hasn't been
verified against this project's specific setup.

- [ ] Not actionable until the [TOOLTEMPEST] CI item is built.
- [ ] When CI exists: confirm whether GitHub's built-in
      failed-workflow email notification is sufficient, or whether a
      custom notification step is needed.

**Source.** Architect chat session, 2026-08-19, sync-tooling.sh
completeness (Phase 5) piece-2 decision discussion.

### P3 — Contributor scoring/reputation for doc-compliant PRs

Found: 2026-08-19, during the ADR-0033 workflow implementation
session, alongside the decision that contributors supply their own
doc updates (see the P1 ADR-0033 entry above). The owner wants some
form of positive signal/recognition for contributors who follow the
project's contribution rules correctly (e.g., include correct doc
updates in their PR on the first attempt) — not yet specified as a
concrete mechanism (could be a PR label, a leaderboard, a badge, a
`CONTRIBUTING.md` acknowledgment, or something else).

This is explicitly unscoped — do not treat any of the above as a
decision. Needs a `/spec` pass to turn into an actionable design once
prioritized; not blocking Part B or ADR-0033's implementation.

- [ ] Needs `/spec` before any implementation.

**Source.** Architect chat session, 2026-08-19, ADR-0033 workflow
implementation session (Part B blocker resolution discussion).
