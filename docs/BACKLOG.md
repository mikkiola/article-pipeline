# Article Pipeline — Backlog

Flat list, priority order. Not a history log (see `docs/adr/` for
decided things, `docs/` git history for what happened). A task moves
here from ROADMAP.md when it's concrete enough to just do; a task
leaves here when it's done or becomes an ADR.

P0 = blocks other work. P1 = should do soon. P2 = someday, not urgent.

## P0

- [ ] Design and build a context/causal-structure layer between Claim
      Extraction and Evidence Package. Claim Extraction's output
      (`novelty` + `basis` fields) drops the source atom's domain/tag
      context and its most concrete details, which is why Evidence
      Package's first live run returned 5/5 unverifiable. Fix this
      before building Strategy Layer, Author, or Quality Gate —
      they'd be built on unreliable input otherwise.
- [ ] Fix `SPEC.md`: it still describes a Bitwarden CLI call for
      reading `LINKUP_API_KEY` in three places. The actual code
      (`evidence_package/search_backend.py`) reads only from the
      environment, no Bitwarden CLI call anywhere. Update the text to
      match.

## P1

- [ ] Decide: keep or drop the confidence-threshold mechanism
      described for Claim Extraction. It may be redundant with the
      interactive assessment Claude Code actually used during the
      pilot — not confirmed either way. Check the code, then decide.
- [ ] Decide: adopt English search-query translation permanently, or
      drop it. Tested on 5 Claims — better for 3, worse for 1, mixed
      for 1. Code exists (`translate_query` in `evidence_package/
      driver.py`) but is not committed.
- [ ] Migrate Atom Selector and `graph_reader.py` from vendored copies
      into this repo as the single source of truth (currently
      duplicated with `brain.git`).
- [ ] Rewrite `README.md` — it still describes an empty-scaffold state
      that hasn't been true since the first real component landed.

## P2

- [ ] Design a support-type classification for Evidence's `verified`
      status (mechanism-supported / outcome-supported /
      semantic-supported / unsupported) instead of the current binary
      criterion. Don't start until the P0 context-layer task above is
      done — changing both at once makes it impossible to tell which
      fix caused which effect.
- [ ] Build the ToolTempest CLI adapter and version-discovery
      mechanism. Manual sync works today; this would make it
      automatic-detection + explicit-install instead.
- [ ] Translate the three remaining Russian-language files in
      `claim_extraction/` to English.
- [ ] Add a second search API backend (Exa) as an alternative to
      Linkup — interface already supports swapping backends, nothing
      built.
- [ ] Set numeric red-flag thresholds for Phase 1 (not yet decided by
      the owner).
- [ ] Set a minimum number of stable days on Habr+LinkedIn before
      adding a third platform (not yet decided).
- [ ] Fix one immutable pilot log line that contains a personal
      filesystem path — do this only when the repo goes public, not
      before (editing an immutable artifact now would break the
      append-only guarantee for no reason yet).
