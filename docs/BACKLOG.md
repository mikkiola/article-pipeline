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

## Tasks

### P0

- [ ] Design and build a context/causal-structure layer between Claim
      Extraction and Evidence Package.

      **Problem:** Claim Extraction produces two text fields,
      `novelty` and `basis`, extracted from a source atom. When
      concatenated as a search query for Evidence Package, the result
      systematically loses: (a) the atom's domain/topic context —
      exists in the atom's tags and wiki-links, but the current
      extraction schema doesn't carry it into `novelty`/`basis`, and
      (b) the most concrete, specific parts of the original claim
      (named examples, named roles, references to current discourse).
      Found by manually comparing the full text of 5 source atoms
      against their extracted `novelty`+`basis` output and confirming
      the same pattern in 4 of the 5 cases — suspected cause of
      Evidence Package's first live run returning 5/5 unverifiable,
      not yet confirmed as the root cause in an ADR. Confirming or
      ruling this out is part of the work.

      **What "design" means:** a written proposal (not code) for a new
      data layer sitting between Claim Extraction's output and
      Evidence Package's input, carrying forward the context that
      `novelty`+`basis` currently drops. Must specify: what new
      field(s) get added, where they're populated from (tags?
      wiki-links? a new extraction step?), and how this interacts with
      the existing `novelty`/`basis` contract without breaking
      whatever already consumes those two fields elsewhere in the
      pipeline.

      **How to produce it:** run a `/spec` session — this project's
      established practice is the Claude Code skill at
      `skills/spec/SKILL.md` (delivered via `mikkiola/tooltempest`,
      synced locally via `scripts/sync-tooling.sh` — run that first if
      `~/.claude/skills/spec/SKILL.md` doesn't exist). If you are the
      architect (in this chat): formulate the task topic/boundary
      below as a message for the owner to paste into Claude Code's
      session — you cannot run `/spec` yourself. If you are Claude
      Code (in the CLI): run `scripts/sync-tooling.sh` if needed, then
      the `/spec` skill directly. Interview topic: exactly the problem
      statement above, nothing more. Do not use this `/spec` run to
      redesign Evidence Package's `verified` criterion (see blocking
      constraint below).

      **Output location:** a new file, `context_layer/SPEC.md`,
      following the same section template as the existing `SPEC.md`
      at repo root (Overview → Goals → Tech Stack → Functional/
      Non-Functional Requirements → Data Model → Test Plan →
      Milestones → Open Questions).

      **Blocking constraint:** do not modify Evidence Package's
      `verified` criterion (in `evidence_package/`) as part of this
      task, even if the `/spec` interview surfaces ideas about it —
      mixing that into this design makes it impossible to tell which
      fix caused which effect later.

      **Done when:** `context_layer/SPEC.md` exists and is committed;
      the owner has read and confirmed it, *and the session ends there
      — do not begin implementation code in the same session, even if
      the owner responds quickly*; a later session implements it; a
      re-run of the 5 original pilot Claims through the new layer
      either confirms or overturns the "5/5 unverifiable" result —
      whichever it is, record that outcome as an ADR.

      If anything above doesn't match what's actually in the repo
      (e.g. `SPEC.md`'s template differs, `scripts/sync-tooling.sh` is
      missing and `~/.claude/skills/spec/SKILL.md` is also missing):
      stop and ask the owner rather than guessing a substitute.
- [ ] Fix `SPEC.md`: it still describes a Bitwarden CLI call for
      reading `LINKUP_API_KEY` in four places. The actual code
      (`evidence_package/search_backend.py`) reads only from the
      environment, no Bitwarden CLI call anywhere. Update the text to
      match.

### P1

- [ ] Commit or discard the uncommitted English search-query
      translation code (`translate_query`, `search_query_en` in
      `evidence_package/driver.py`). It is not currently committed, so
      a fresh clone of this repo does not have it — first step is
      deciding whether to commit it at all, not deciding what to do
      with code a new session can't see. Test results so far: better
      for 3 of 5 Claims, worse for 1, mixed for 1. Once committed (or
      explicitly discarded), decide: adopt permanently or drop.
      Chinese-language translation was not attempted — separate,
      later decision, not blocked on the English one.
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
