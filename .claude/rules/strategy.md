---
paths:
  - "strategy_layer/**"
  - "author/**"
---

# Strategy and authoring boundaries

Read the current root [SPEC](../../SPEC.md), relevant accepted decisions and
[pyproject.toml](../../pyproject.toml) before changing these packages.
The import-linter contract there is the source for the Anti-Corruption Layer's
forbidden imports; do not duplicate its module list in these instructions.
Use established adapters/contracts for source data and existing component tests
for policy changes. Draft generation is not evidence of publication or approval.
