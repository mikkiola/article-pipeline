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
