---
id: ADR-0048
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0048: Source-Independence via Anti-Corruption Layer Architecture

## Status

Accepted.

## Context & Constraints

Strategy Layer's core decision logic (`pre_filter.py`, `framing.py`,
`write_verdict.py`) was hardcoded to Brain's Claim/Evidence shape
(`SPEC.md`'s predecessor state, `docs/ARCHITECTURE.md`'s Strategy
Layer row before this sprint) — single-source only, not source-
independent, despite R3 ("adding a source touches only its own
adapter") already being a stated requirement. Collector needed to
become a real second source this sprint, for both LinkedIn (rewiring
an existing bypass) and Habr (a new entry point), without Strategy
Layer's core logic learning anything about either source's raw shape.

## Decision

**Anti-Corruption Layer / Ports-and-Adapters.** Strategy Layer defines
one inbound Pydantic contract (`CanonicalUnit`,
`strategy_layer/contract.py`, see ADR-0047 for its two-dimension
fields). Each source gets its own adapter
(`strategy_layer/adapters/collector.py` this sprint; Brain's own
adapter explicitly deferred) translating raw source data into that
contract. `pre_filter.py`/`framing.py`/`write_verdict.py` never read a
source-specific field directly — enforced structurally (M6, this
sprint) via an import-linter forbidden-import contract and a
grep-based path-hardcoding lint, not by convention alone.

**YAGNI on the contract's shape.** `CanonicalUnit`'s fields were built
from the intersection of what Brain's Claim/Evidence pair and
Collector's telemetry actually need to express today (`unit_id`,
`source`, `integrity_status`, `corroboration_status`,
`assertion_text`, `source_url`, `license`, a `metadata` passthrough
bag) — not the union of every field either source's full data model
theoretically has. Brain-specific fields that don't generalize (e.g.
`context` — tags/wiki_links from the Context layer) are left out of
the canonical shape entirely and pushed into `metadata` for a future
Brain adapter to populate, rather than speculatively added to the
contract now for a source that isn't wired yet.

**Extend Strategy Layer's own input contract, not a separate
Normalization Layer.** Considered and rejected: introducing a new,
standalone Normalization Layer/service sitting in front of Strategy
Layer, translating all sources into a shared shape before Strategy
Layer sees anything. Chosen instead: `CanonicalUnit` is Strategy
Layer's own inbound contract — the ACL boundary is Strategy Layer's
input, not a new component upstream of it. This keeps the boundary
where R3 already placed responsibility (an adapter is source-specific
integration code, not a new architectural layer) and avoids adding a
service/module whose only job would be re-deriving what
`CanonicalUnit`'s `model_validator` (Pydantic construction-time
validation) already enforces for free at the point each adapter
constructs its output.

## Precedent Basis

Reviewed for precedent, not adopted wholesale:

- **Singer / Meltano** — tap/target pattern: each source ("tap")
  extracts into a common message protocol, each destination ("target")
  consumes it, neither side needs to know the other's shape. Mirrors
  adapter-per-source producing a shared contract.
- **Airbyte** — connector-per-source architecture with a shared
  internal message format (AirbyteRecordMessage), same tap/target
  lineage as Singer, at larger scale.
- **Haystack** — component/pipeline architecture where each node
  declares typed inputs/outputs and a shared document/answer schema
  moves between them; informs the "core logic only knows the
  canonical shape, never a component's internal representation"
  discipline applied here to `pre_filter.py`/`framing.py`.
- **Dagster** — software-defined assets with typed I/O between ops;
  informs treating `CanonicalUnit` as a first-class typed contract
  boundary (Pydantic validation at construction) rather than an
  informally-shaped dict passed between functions.

None of these four is a claim-verification or evidence pipeline —
they're general data-integration/orchestration tools. The precedent
taken from them is structural (adapter-per-source into one shared
typed contract, core logic decoupled from any one source's shape), not
domain-specific; the two-dimension verification content that shape
carries is this project's own (ADR-0047), not borrowed from any of
these four.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| **A. Standalone Normalization Layer, a new component upstream of Strategy Layer.** | Rejected. Adds a new architectural component and its own deployment/testing surface for a boundary `CanonicalUnit`-as-inbound-contract already provides. Also blurs R3's stated boundary ("adding a source touches only its own adapter") by giving a second component (the normalization service) a reason to also change when a source is added. |
| **B. No shared contract — each source's adapter writes directly into `pre_filter.py`'s existing dict shape, source-specific branches added inside the core logic as needed.** | Rejected. This is the pre-sprint state (hardcoded to Brain's Claim/Evidence shape) — exactly what R3 and this sprint exist to fix. Adding Collector this way would mean `pre_filter.py`/`framing.py` growing `if source == "collector"` branches, the coupling this migration removes. |
| **C. Chosen — Anti-Corruption Layer: `CanonicalUnit` as Strategy Layer's own inbound Pydantic contract, one adapter per source, core logic reads only the canonical shape, structurally enforced (import-linter + grep-lint + alien-source contract test).** | Satisfies R3 by construction — a new source's integration work is entirely contained in its own adapter file, verified by M6's synthetic alien-source contract test proving the core logic needs no changes to accept a source it has never seen. No new component beyond what Strategy Layer already is; the contract lives where the boundary naturally sits. |

## Consequences

- `strategy_layer/adapters/collector.py` is the only file that reads
  Collector's raw `manifest_*.json`/`daily_brief_*.json` shape;
  `pre_filter.py`/`framing.py`/`write_verdict.py` see only
  `CanonicalUnit` instances.
- Brain's own adapter remains unbuilt (explicit sprint scope
  boundary, `SPEC.md`'s Out of Scope) — this ADR's architecture is
  designed with Brain's shape in view (`context` deferred into
  `metadata`) but does not implement it.
- M6 (this sprint) enforces the boundary mechanically: an
  import-linter `forbidden` contract
  (`strategy_layer.{pre_filter,framing,write_verdict,derivation_kind}`
  forbidden from importing `claim_extraction`/`context_layer`/
  `evidence_package`/`author.source_adapter`), a grep-based lint
  against hardcoded source-specific path strings in those same core
  files, and a synthetic alien-source contract test constructing a
  `CanonicalUnit` for a source the core logic has never seen.
- `AuthoringContext` (ADR-0045) is a deliberate, later addition to this
  same architecture, not a competing one — it is built *after*
  classification, from already-`include`d `CanonicalUnit`s, and stays
  out of `strategy_layer/`'s own package so the ACL boundary this ADR
  establishes remains a real directory boundary, not a convention.

## Confirmation & Revisit

Validated by construction: M1-M5's real end-to-end runs against live
Collector data through the `CanonicalUnit` boundary (see each
milestone's `done:` entry in `SPEC.md`), and M6's mechanical
enforcement (import-linter, grep-lint, alien-source contract test —
see this repo's own CI implementation for literal pass/fail output).

Revisit when Brain's own adapter is built: confirm `CanonicalUnit`'s
current field set (built from the Brain+Collector *intersection*,
YAGNI) still covers what Brain's Claim/Evidence pair needs, or extend
it via a new ADR (Immutable Lineage, `docs/adr/0011`) if it doesn't —
not assumed to be sufficient sight unseen.

## Source

Owner decision, architect-chat, 2026-09-14, 4-AI consensus session
(per `SPEC.md`'s Architecture section) preceding the `/spec` interview
that produced this sprint's `SPEC.md` — the ACL/Ports-and-Adapters
pattern, the YAGNI contract-shape reasoning, the extend-not-separate-
layer choice, and the four-tool precedent survey were decided there
and are already reflected in `SPEC.md`'s Architecture section; this
ADR is the catch-up record `docs/CONSTITUTION.md`'s doc-currency rule
requires, not a new decision.
