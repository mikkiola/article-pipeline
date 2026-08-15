# Article Pipeline — Architecture

State as of 2026-08-14. Every fact is a table cell — no prose
sections. Rationale for any decision: `docs/adr/`. Plan:
`docs/ROADMAP.md`. Tasks: `docs/BACKLOG.md`. This document does not
duplicate what those three own — it states current state and
dependencies only.

| Component | Status | Depends on | Validation | Commit |
|---|---|---|---|---|
| Atom Selector | Implemented | Brain (`02_Cards/`) | Tested on real data | `bd7b784`, bugfix `97b87f7` |
| `graph_reader.py` | Implemented | Atom Selector | Tested on real data | `e7fbc45` |
| Claim Extraction | Implemented | Atom Selector, `graph_reader.py` | 4 immutable pilot runs, manually verified | `46d1a41` |
| Context/causal-structure layer | Spec only | Claim Extraction | — | `context_layer/SPEC.md` (`cddf498`) |
| Evidence Package | Implemented | Claim Extraction output | 5 live Claims tested, 5/5 unverifiable | `2fe0aac..29f716f` |
| Strategy Layer | Spec only | Context/causal-structure layer | — | — |
| Author | Spec only | Strategy Layer | — | — |
| Quality Gate | Spec only | Author | — | — |
| Platform Adapter | Spec only | Quality Gate | — | — |
| Experiment Log | Spec only | Platform Adapter | — | — |
| ToolTempest lock+sync (manual) | Implemented | `mikkiola/tooltempest` | End-to-end tested, byte-for-byte diff verified | `3d4ad09` |
| ToolTempest CLI adapter + discovery | Not started | ToolTempest lock+sync | — | — |

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
