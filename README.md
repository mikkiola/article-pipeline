# Article Pipeline

Article Pipeline — a publishing conveyor for technical articles (Habr +
LinkedIn): claim extraction, evidence gathering, strategy layer, authoring,
quality gate, and platform adaptation.

Canonical documentation (Constitution, Architecture, Causal Memory) lives
in Google Drive (Article_Pipeline), not in this repository.

This repository currently holds only the structural scaffold. Code and
migration history from `brain.git` will land as a separate task.

Authoring now has a first MVP implementation: it drafts Habr/LinkedIn
articles from Collector's data, now routed through the strategy
layer's verdict rather than read directly — see
`docs/adr/0043-author-mvp-single-source-pilot.md` for the original
pilot architecture and `docs/adr/0045-post-classification-authoring-
context.md`/`docs/adr/0046-habr-multi-claim-digest.md` for how it's
wired today; full per-component status is in `docs/ARCHITECTURE.md`.
