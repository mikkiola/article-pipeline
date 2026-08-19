# Article Pipeline — Architecture

State as of 2026-08-19. Every fact is a table cell — no prose
sections. Rationale for any decision: `docs/adr/`. Plan:
`docs/ROADMAP.md`. Tasks: `docs/BACKLOG.md`. This document does not
duplicate what those three own — it states current state and
dependencies only.

| Component | Status | Depends on | Validation | Commit |
|---|---|---|---|---|
| Atom Selector | Implemented | Brain (`02_Cards/`) | Tested on real data | `brain.git: bd7b784`, bugfix `97b87f7` (vendored copy; not migrated to single source) |
| `graph_reader.py` | Implemented | Atom Selector | Tested on real data | `brain.git: e7fbc45` (vendored copy; not migrated to single source) |
| Claim Extraction | Implemented | Atom Selector, `graph_reader.py` | 4 immutable pilot runs, manually verified | `46d1a41` |
| Context/causal-structure layer | Implemented | Claim Extraction | M1-M5 complete; context-loss hypothesis not established (see corrective ADR for this milestone) | `792feb0`..`d2050de` |
| Evidence Package | Implemented | Claim Extraction output | 5 live Claims tested, 5/5 unverifiable | `2fe0aac..29f716f` |
| Strategy Layer | Not started | Context/causal-structure layer | — | — |
| Author | Not started | Strategy Layer | — | — |
| Quality Gate | Not started | Author | — | — |
| Platform Adapter | Not started | Quality Gate | — | — |
| Experiment Log | Not started | Platform Adapter | — | — |
| ToolTempest DocOps Protocol (pre-commit/pre-push hooks + Drift Warning) | Implemented | `mikkiola/tooltempest` (pinned via `.tooltempest.lock`) | Regression-tested: RECONCILE, HARD BLOCK (staged/unstaged conflict, UNKNOWN-pattern), crash-vs-content-problem messages, Drift Warning — see ADR-0001 (`mikkiola/tooltempest`), ADR-0032 (this repo) | `.tooltempest.lock` pinned at `5fb62a9`; Drift Warning `404c24c` |
| ToolTempest Tier 2 doc-sync (snapshot, diff, role-gated apply, CLI) | Implemented | ToolTempest DocOps Protocol | Tested via scratch scenarios against real git repos, Stage 2-4: snapshot/diff generation; atomic rollback on rejection; dirty-pre-invocation-state preservation; constrained non-interactive mode; invalid-input-as-rejection; exception-mid-flow rollback; CLI JSON validation (keys outside `TIER2_DOCS`, missing file, malformed JSON) — see ADR-0002/ADR-0003 (`mikkiola/tooltempest`). Vendored as `scripts/doc_sync_tier2.py` (gitignored, same convention as `doc_sync.py`). Contributor-governance workflow built on top (GitHub Actions, PR-as-confirmation) is a separate, not-yet-implemented design — see ADR-0033 (this repo) | `doc_sync_tier2.py` at `mikkiola/tooltempest@5fb62a9`; vendored into this repo `f51c528` |
| ToolTempest CLI adapter + discovery | Not started | ToolTempest DocOps Protocol | — | — |

## Repositories

| Repo | Contains |
|---|---|
| `lyolich777ka/brain.git` | Brain (Obsidian graph), Drift/Collision Engine, original Atom Selector |
| `mikkiola/article-pipeline` | This project's code + `docs/adr/` |
| `mikkiola/tooltempest` | Shared tooling (`/spec`, `/verify`, `drift-control.md`) |

## Models used by this project

| Component | Model or service |
|---|---|
| Claim Extraction | Interactive, Claude Code |
| Evidence Package | Linkup API (search/retrieval, not a language model) |
