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
| 3 — Strategy Layer + Author + Quality Gate | Paused — Author has a separate, single-source MVP pilot (Collector-manifest-based, not fed by Strategy Layer); Strategy Layer and Quality Gate proper remain not started; see Current pointer |
| 4 — Platform Adapter (Habr → LinkedIn) + Circuit Breaker | Not started |
| 5+ — Experiment Log, remaining platforms | Not started |

## Current pointer

- Phase 2.5's causal question is resolved, partially confirmed (see
  Status table above) — Phase 3 is no longer blocked on it. The
  atom-tag-disambiguation P1 item found via the same experiment is a
  targeted, non-blocking follow-up — see `docs/BACKLOG.md`.
- Phase 3 scope explicitly includes monetization-related requirements
  for Platform Adapter and Experiment Log — see `docs/BACKLOG.md`'s
  `[B-045]`/`[B-046]`.
- A Multi-Source Claim Layer expansion (Brain + Radar + ODS + repos as
  claim sources) is under architectural discussion, not started —
  paused pending Radar's and Brain's in-progress migration to GitHub.
- Extensive monetization-loop modeling, for both the owner's own
  pipeline and a separate sellable client-template product, was
  completed 2026-08-27/28 — full record in `docs/BACKLOG.md`'s
  `[B-045]`/`[B-046]`/`[B-050]`/`[B-051]`/`[B-052]`. The session
  concluded with an explicit decision to stop further monetization
  analysis and resume Phase 3.
- Collector (O1), a separate, standalone sibling initiative in its own
  private repo, has started outside this repo's scope — no
  article-pipeline phase or component is affected; see
  `docs/BACKLOG.md`'s `[B-055]` for detail.
- **Priority shift, this session:** the active focus has moved from
  Phase 3 planning (Multi-Source Claim Layer / Strategy Layer
  expansion) to validating the publication channel itself — a
  single-source pilot (Collector's manifest -> Author -> two drafts,
  Habr RU + LinkedIn EN) built and reviewed this session (Author's
  first implementation; see `docs/ARCHITECTURE.md`'s Author row and
  `docs/adr/0043-author-mvp-single-source-pilot.md`). Multi-Source
  Claim Layer / Strategy Layer Phase 3 work, and Radar/Brain as claim
  sources, are **paused, not abandoned** — resume once the pilot
  confirms publication mechanics actually work end-to-end. See
  `docs/BACKLOG.md`'s `[B-056]` for the full record of what's paused
  and why.

Next work continues the single-source pilot (owner review of the
generated drafts, then whichever follow-up that review points to) —
not Phase 3 planning, per the priority shift above.

## Dependency chain

Derived from `docs/ARCHITECTURE.md`'s "Depends on" column — keep this
table consistent with that source; do not edit dependency data here
independently of it.

| Component | Depends on |
|---|---|
| Context/causal-structure layer | Claim Extraction |
| Evidence Package | Claim Extraction output |
| Strategy Layer | Context/causal-structure layer |
| Author | Collector (pilot; not yet Strategy Layer) |
| Quality Gate | Author |
| Platform Adapter | Quality Gate |
| Experiment Log | Platform Adapter |

## Open decisions

See `docs/BACKLOG.md`'s "Owner decisions needed" section.
