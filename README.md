# Article Pipeline

Article Pipeline — a publishing conveyor for technical articles (Habr +
LinkedIn): claim extraction, evidence gathering, strategy layer, authoring,
quality gate, and platform adaptation.

Canonical documentation (Constitution, Architecture, Causal Memory) lives
in Google Drive (Article_Pipeline), not in this repository.

This repository currently holds only the structural scaffold. Code and
migration history from `brain.git` will land as a separate task.

Authoring now has a first MVP implementation: a single-source pilot
that drafts Habr/LinkedIn articles from Collector's manifest, not yet
fed by the strategy layer — see `docs/adr/0043-author-mvp-single-
source-pilot.md`; full per-component status is in
`docs/ARCHITECTURE.md`.
