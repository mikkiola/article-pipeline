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
| 3 — Strategy Layer + Author + Quality Gate | In progress — Strategy Layer is now Collector-sourced and source-independent for Collector specifically (two-dimension `CanonicalUnit` contract, Collector adapter, CI-enforced ACL boundary; Brain's own adapter not yet built); Author (both LinkedIn and Habr) now consumes Strategy Layer's verdict, no longer reads Collector directly (see `docs/ARCHITECTURE.md`); Quality Gate proper remains not started; see Current pointer |
| 4 — Platform Adapter (LinkedIn → Habr) + Circuit Breaker | Not started |
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
- **Priority shift** (historical record, since resolved — see next
  bullet): the active focus moved from Phase 3 planning (Multi-Source
  Claim Layer / Strategy Layer expansion) to validating the
  publication channel itself — a single-source pilot (Collector's
  manifest -> Author -> two drafts, Habr RU + LinkedIn EN) built and
  reviewed that session (Author's first implementation; see
  `docs/ARCHITECTURE.md`'s Author row and
  `docs/adr/0043-author-mvp-single-source-pilot.md`). Multi-Source
  Claim Layer / Strategy Layer Phase 3 work, and Radar/Brain as claim
  sources, were **paused, not abandoned** — resume once the pilot
  confirmed publication mechanics actually worked end-to-end. See
  `docs/BACKLOG.md`'s `[B-056]` for the full record of what was paused
  and why.
- **Resume condition met, 2026-09-16.** `[B-056]`'s own stated resume
  condition — Strategy Layer becoming source-independent enough to
  consume Collector — is built and committed to `main` (pushed to
  `origin/main`): the two-dimension `CanonicalUnit` contract, Collector's
  adapter, both LinkedIn and Habr routed through Strategy Layer's
  verdict, and CI enforcement of the Anti-Corruption-Layer boundary
  (M1-M7, commits `c912c28`..`228d251`; rationale in `docs/adr/`, see
  `docs/ARCHITECTURE.md`'s Strategy Layer and Author rows). `[B-056]`
  carries a dated note confirming this; see also `docs/BACKLOG.md`'s
  `[B-063]` for the sprint's own record. Phase 3 planning/
  implementation has resumed on this basis, per the Status table
  above ("In progress").

Next work is the Publication Core Loop (row 1 of the committed phase order below):
the first automatic publication on LinkedIn, then Habr. Prerequisites are the R6
decision (see the open questions below) and a publication registry — see
`docs/BACKLOG.md`'s `[B-064]`. Brain's own adapter, the atom-tag-disambiguation
follow-up (`[B-005]`), and Quality Gate remain not started and follow the committed
phase order.

## Committed phase order (confirmed 2026-09-18)

Assembled here for the first time as one ordered sequence — the
individual pieces were already scattered across this document,
`docs/BACKLOG.md`, and `docs/PROJECT.md`; no document previously stated
this order as a single plan.

| Order | Phase | Status | Notes |
|---|---|---|---|
| 1 | Publication Core Loop — LinkedIn and Habr both publish automatically, end to end, on real data | COMMITTED | Per `docs/PROJECT.md`'s Definition of Done. Requires a publication registry before the first automatic run — see `docs/BACKLOG.md`'s `[B-064]`. LinkedIn first, then Habr. |
| 2 | Cleanup / dead-code / obsolete-directory consolidation | COMMITTED | No dedicated `docs/BACKLOG.md` entry yet — see `[B-063]`'s "Explicitly deferred" note (`story_builder.py`/`channel_author.py` Collector-vocabulary leak) |
| 3 | Additional sources via the existing adapter pattern — Brain | COMMITTED, paused | Brain already named above (paused, blocked on Brain's GitHub migration); Archi-kg is not recorded as a claim source anywhere in this repo's docs and is not included in this phase |
| 4 | Source-independent architecture matured enough to add a new source without changing downstream logic | COMMITTED | The mechanism (per-source adapters, Anti-Corruption-Layer boundary) already exists today for Collector — see `docs/ARCHITECTURE.md`'s Strategy Layer row; this phase is about adding more sources through it, not building the mechanism itself |
| 5 | Self-service / external-user source configuration | see `[B-046]` | Sequence position only — the item itself remains `[B-046]`'s own deferred hypothesis: "none to be implemented before `[B-045]` is built and produces real usage data" |

## Committed content requirements (confirmed 2026-09-18, not yet built)

| Channel | Requirement | Status | Notes |
|---|---|---|---|
| LinkedIn | Problem → search → solution narrative structure (not an activity list) | COMMITTED, not yet built | The existing LinkedIn daily-post voice contract's Decision specifies a different structure — "Narrative Bridge 30/40/30 + hook + CTA + evidence links" — not this problem→search→solution framing; this requirement is a distinct addition, not something that contract already covers |
| Habr | At least one code/artifact fragment and at least one externally-sourced enrichment per article | COMMITTED, not yet designed | Confirmed absent from every canonical doc under any name (code snippet, artifact fragment, external source, web enrichment) |

## Open questions — committed phase order (confirmed 2026-09-18)

Unresolved — not scheduled work, matching `docs/BACKLOG.md`'s "Owner
decisions needed" style:

- Does R6's ≥1-verified-external-claim publish gate apply to the
  Collector-only daily LinkedIn path the same way it applies to the
  Brain/Strategy-Layer path? Not yet decided.
- How does Habr's code/artifact-fragment requirement (above) get its
  evidence — no source exists today for actual code/diff content. Not
  yet decided.
- Should Archi-kg be a claim source at all, and if so, on what basis?
  Not previously decided anywhere.
- Multi-week direction/trajectory capability — being defined in a
  separate repository, `mikkiola/analyzer`; not described here.
- Does Habr offer a supported way to publish an article without a manual step? An
  unofficial client for an old Habr API and a 2017 browser-cookie method exist. Neither
  is confirmed as current and supported. Not yet verified.

## Dependency chain

Derived from `docs/ARCHITECTURE.md`'s "Depends on" column — keep this
table consistent with that source; do not edit dependency data here
independently of it.

| Component | Depends on |
|---|---|
| Context/causal-structure layer | Claim Extraction |
| Evidence Package | Claim Extraction output |
| Strategy Layer | Context/causal-structure layer, Collector |
| Author | Strategy Layer |
| Quality Gate | Author |
| Platform Adapter | Quality Gate |
| Experiment Log | Platform Adapter |

## Open decisions

See `docs/BACKLOG.md`'s "Owner decisions needed" section.
