# Article Pipeline — Roadmap

Phases, sequencing, dependencies, and the current execution pointer
only. No task instructions, requirements, acceptance criteria, or
implementation detail — see `docs/BACKLOG.md` for that. No rationale —
see `docs/adr/`.

## Status

| Phase | Status |
|---|---|
| 0 — Scaffold + `graph_reader.py` | Closed |
| 1 — Claim Extraction pilot | Closed |
| 2 — Evidence Package | Closed |
| 2.5 — Context/causal-structure layer | Next — not started |
| 3 — Strategy Layer + Author + Quality Gate | Blocked on 2.5 |
| 4 — Platform Adapter (Habr → LinkedIn) + Circuit Breaker | Not started |
| 5+ — Experiment Log, remaining platforms | Not started |

## Current pointer

Work the P0 items in `docs/BACKLOG.md`. Phase 2.5 (context layer) is
the current phase; Phase 3 stays blocked until it's done. Do not begin
Phase 3 work before Phase 2.5 closes.

## Dependency chain

```
Claim Extraction
  → Context/causal-structure layer (Phase 2.5, current)
    → Evidence Package reliability
      → Strategy Layer / Author / Quality Gate (Phase 3, blocked)
        → Platform Adapter (Phase 4)
          → Experiment Log, additional platforms (Phase 5+)
```

## Open decisions

See `docs/BACKLOG.md`'s "Owner decisions needed" section.
