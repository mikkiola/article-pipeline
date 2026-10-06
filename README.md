# Article Pipeline

Article Pipeline — a publishing conveyor for technical articles (Habr +
LinkedIn): claim extraction, evidence gathering, strategy layer, authoring,
quality gate, and platform adaptation. Claim extraction, evidence gathering,
the strategy layer and authoring exist; the quality gate and platform
adaptation are not started — see `docs/ARCHITECTURE.md`.

Canonical documentation lives in `docs/`: the Constitution, Project,
Architecture, Roadmap and Backlog documents, and the decision records
under `docs/adr/`.

Atom Selector and `graph_reader.py` currently live here as vendored copies
of `brain.git` code; migrating them to a single source is open as `[B-002]`
in `docs/BACKLOG.md`.

Authoring now has a first MVP implementation: it drafts Habr/LinkedIn
articles from Collector's data, now routed through the strategy
layer's verdict rather than read directly — see
`docs/adr/0043-author-mvp-single-source-pilot.md` for the original
pilot architecture and
`docs/adr/0045-post-classification-authoring-context.md`/`docs/adr/0046-habr-multi-claim-digest.md`
for how it's wired today; full per-component status is in
`docs/ARCHITECTURE.md`.
