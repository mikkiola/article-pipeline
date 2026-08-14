# Article Pipeline — Architecture

State as of 2026-08-14. One table, no prose. Rationale for any
decision: `docs/adr/`. Plan: `ROADMAP.md`. Tasks: `BACKLOG.md`.

Project: publishes articles to Habr and LinkedIn, built from atoms in
an Obsidian knowledge graph (Brain). Separate from System Drift
(Telegram, Collision Engine) — different project, split 2026-07-30.

| Component | Status | Commit | Notes |
|---|---|---|---|
| Atom Selector | Implemented | `bd7b784`, bugfix `97b87f7` | Vendored copy in this repo, not migrated to single source |
| `graph_reader.py` | Implemented | `e7fbc45` | Vendored copy in this repo, not migrated to single source |
| Claim Extraction | Implemented | `46d1a41` | 4 immutable pilot runs; output loses context needed downstream, unresolved |
| Evidence Package | Implemented | `2fe0aac..29f716f` | Validated on 5 live Claims, 5/5 unverifiable — root cause traced to Claim Extraction, not this component |
| ToolTempest lock+sync (manual) | Implemented | `3d4ad09` | Manual only — no CLI adapter, no auto-discovery |
| ToolTempest CLI adapter + discovery | Not started | — | Architectural contract fixed, nothing built |
| Context/causal-structure layer | Not started | — | Fixes Claim Extraction's context loss; see BACKLOG.md P0 |
| Strategy Layer | Spec only | — | Blocked until context layer exists |
| Author | Spec only | — | Blocked until context layer exists |
| Quality Gate | Spec only | — | Blocked until context layer exists |
| Platform Adapter | Spec only | — | Blocked until context layer exists |
| Experiment Log | Spec only | — | Blocked until context layer exists |

## Repositories

| Repo | Contains |
|---|---|
| `lyolich777ka/brain.git` | Brain (Obsidian graph), Drift/Collision Engine, original Atom Selector |
| `mikkiola/article-pipeline` | This project's code + `docs/adr/` |
| `mikkiola/tooltempest` | Shared tooling (`/spec`, `/verify`, `drift-control.md`) |

## Models

| Use | Model |
|---|---|
| Drift primary | `claude-sonnet-5` |
| Drift fallback | `claude-sonnet-4-6` |
| Claim Extraction | Interactive, Claude Code |
| Evidence Package | Linkup API |
