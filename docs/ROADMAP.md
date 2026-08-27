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
| 2.5 — Context/causal-structure layer | Closed — M1-M5 implemented; causal question resolved, partially confirmed: enrichment helps on-domain, harms via polysemous-tag collision, tracked as a non-blocking P1 fix. Phase 3 no longer blocked on this. |
| 3 — Strategy Layer + Author + Quality Gate | Not started — no longer blocked (see Current pointer) |
| 4 — Platform Adapter (Habr → LinkedIn) + Circuit Breaker | Not started |
| 5+ — Experiment Log, remaining platforms | Not started |

## Current pointer

Phase 2.5's causal question is resolved, partially confirmed — the
P0 item that tracked it is done and removed from
`docs/BACKLOG.md`'s P0 section, which is now empty. Phase 3 is no
longer blocked on this question. The atom-tag-disambiguation P1 item
(found via the same experiment) is a targeted, non-blocking follow-up
— see `docs/BACKLOG.md`. Next work can pull from P1 items or begin
Phase 3 planning.

Phase 3 scope now explicitly includes monetization-related
requirements for Platform Adapter and Experiment Log (see
`docs/BACKLOG.md`'s `[B-045]`/`[B-046]`). A Multi-Source Claim Layer
expansion (Brain + Radar + ODS + repos as claim sources) is under
architectural discussion but not yet started — Radar and Brain are
mid-migration to GitHub as of this entry, and that work is explicitly
paused pending migration completion.

## Dependency chain

```
Claim Extraction
  → Context/causal-structure layer (Phase 2.5, closed)
    → Evidence Package reliability
      → Strategy Layer / Author / Quality Gate (Phase 3, not started)
        → Platform Adapter (Phase 4)
          → Experiment Log, additional platforms (Phase 5+)
```

## Open decisions

See `docs/BACKLOG.md`'s "Owner decisions needed" section.
