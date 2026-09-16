---
id: ADR-0047
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0047: Two-Dimension Verification Model (Integrity × Corroboration)

## Status

Accepted.

## Context & Constraints

Strategy Layer's original status vocabulary — `verified` / `disputed` /
`unverifiable` / `pending` — was built for exactly one shape of input:
a Brain Claim paired with an Evidence record from an external search
API. It answers one question ("was this assertion corroborated by an
external source?") and assumes every unit it's applied to is making an
assertion in the first place.

This sprint's source-independence work (`SPEC.md`) needed the same
gate to also accept Collector's raw telemetry — commit counts,
diffstats, repo activity. A Collector record makes no falsifiable
claim: a commit either happened or it didn't, and Collector's own scan
either reflects that accurately or it doesn't. Forcing this shape into
the old vocabulary produces two bad options: label it `unverifiable`
(implying a corroboration attempt was made and failed, when none was
ever applicable), or invent a fabricated corroboration step for
something with nothing to corroborate. Both misrepresent what actually
happened to the record, which is the failure mode this decision exists
to avoid.

## Decision

Replace the single status with two independent dimensions, not a
richer single enum:

1. **`integrity_status`** (`valid` / `invalid`) — applies to every
   unit, from every source, no exceptions. Answers: is this record
   authentic and provenanced as what it claims to be? For Collector,
   this is the repo+branch-existence and commit-count-reconciliation
   check (`strategy_layer/adapters/collector.py`); Brain's own adapter
   (deferred past this sprint) would answer it differently, but the
   dimension itself is source-agnostic.
2. **`corroboration_status`** (`corroborated` / `disputed` /
   `unsubstantiated` / `pending` / `not_applicable`) — applies only to
   units making a falsifiable assertion. `not_applicable` is a
   first-class value, not an absence of data: it says plainly that
   this record asserts nothing external corroboration could confirm or
   deny.

`integrity_status` is checked first and acts as a hard floor
(`invalid` excludes regardless of `corroboration_status`) — an
inauthentic record is worthless independent of what it claims.
`corroboration_status` then governs everything downstream of
authenticity: whether an assertion, if one exists, has been checked
against the outside world. This is why the two are modeled as
orthogonal dimensions rather than levels of one richer status — a unit
can be authentic and uncorroborated, authentic and disputed, or
authentic with nothing to corroborate at all, and each of those is a
materially different situation for a downstream consumer to reason
about.

## Precedent Basis

Reviewed for precedent, not adopted wholesale:

- **in-toto / SLSA** — separate provenance attestation (what produced
  this artifact, is the chain of custody intact) from any claim about
  the artifact's content being true. `integrity_status` mirrors this:
  a provenance/authenticity check, independent of assertion content.
- **W3C PROV-O / Verifiable Credentials** — separate the
  subject/predicate (what is being asserted) from the
  issuer/attestation (who backs it and how). `corroboration_status`
  plays the attestation role here — has an external source backed this
  specific assertion.
- **Nanopublications** — the same subject/predicate vs.
  provenance/publication-info split, applied at the level of a single
  atomic scientific claim rather than a whole document.

**No existing standard in this survey unifies claim-verification and
pure-record-provenance under one shared gate the way this model does**
— each of the above separates authenticity from assertion-content
within a single kind of record; none of them was built to also pass a
non-asserting raw record (Collector's telemetry) through the same gate
as an asserting one. The two-dimension model here is a stated novel
synthesis for this project's specific need (one gate covering both
Brain's Claims and Collector's bare records), not an adopted external
standard.

**Pearl's ladder of causation** is used as a correction lens, not a
citation of authority: a bare record (a commit happened) sits outside
the ladder entirely until someone derives an inference from it
(association, intervention, or counterfactual language). This is the
principle `derivation_kind` (`restatement` / `aggregation` /
`evaluation` / `causal_claim`,
`strategy_layer/derivation_kind.py`) implements one layer downstream,
at framing time: a `not_applicable` unit's raw fact does not
automatically license a causal or evaluative sentence about it just
because framing text was generated. The two-dimension model at
ingestion and `derivation_kind` at framing are the same underlying
discipline — don't let a status or a sentence claim more verification
or inferential weight than what actually happened — applied at two
different points in the pipeline.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| **A. Extend the single-status enum** (add e.g. `not_applicable` as a fifth value alongside `verified`/`disputed`/`unverifiable`/`pending`). | Rejected. A single enum conflates two questions — is this authentic, and is its assertion corroborated — into one axis. `invalid`-but-`corroborated` and `valid`-but-`unsubstantiated` are both real, distinguishable situations a single enum can't represent without exponentially growing compound values. |
| **B. Two boolean flags instead of two enums** (`is_authentic`, `is_corroborated`). | Rejected. Loses information a boolean can't carry: `corroboration_status` needs to distinguish `not_applicable` (nothing to corroborate) from `pending` (corroboration attempted, not yet resolved) from `unsubstantiated`/`disputed` (corroboration attempted and failed differently) — collapsing these to true/false erases the distinction R6/R8 depend on. |
| **C. Chosen — two independent enum dimensions, `integrity_status` as a hard floor, `corroboration_status` including `not_applicable` as first-class.** | Represents each of the real, distinguishable situations a unit can be in without inventing compound states, generalizes cleanly to a source (Collector) that was never designed to make assertions at all, and keeps the pre-filter classification table (`SPEC.md`'s Pre-Filter Classification section) a simple 6-row lookup over the two dimensions rather than a hand-maintained compound enum. |

## Consequences

- `strategy_layer/contract.py`'s `CanonicalUnit` carries both fields
  plus the `model_validator` enforcing their consistency (R8:
  `corroborated` requires non-empty `source_url`/`license`;
  non-`not_applicable` requires non-empty `assertion_text`).
- `pre_filter.py`'s classification table and gate condition
  (`zero_included_units`, replacing `all_claims_unverifiable`) are
  keyed off both dimensions — `SPEC.md`'s Pre-Filter Classification /
  Gate Condition sections, already implemented (M1/M2).
- R6 is restated (not silently reinterpreted) in two-dimension terms:
  a published piece needs ≥1 `integrity_status=valid` unit, and any
  unit with an applicable `corroboration_status` must be
  `corroborated`, not `unsubstantiated`/`pending` — this is what lets
  a Collector-only, all-`not_applicable` draft satisfy R6 on integrity
  alone.
- `derivation_kind.py`'s rule table (M3) is the same discipline applied
  one layer downstream, at framing time, per the Pearl's-ladder note
  above — recorded here as the same principle, not re-litigated as a
  separate decision.

## Confirmation & Revisit

Validated by construction: `strategy_layer/test_contract.py` (10/10 —
`extra="forbid"` rejection, `frozen=True` mutation-block, all
`model_validator` consistency rules), the rewritten
`strategy_layer/test_pre_filter.py` (11/11 — 6-row classification
matrix, `zero_included_units` gate, RED-before/GREEN-after per
`docs/CONSTITUTION.md`'s TDD rule), and a real end-to-end run against
live Collector data (`strategy_layer/run_collector_pilot.py`,
`strategy_layer/output/verdict_20260915T191323.json`).

Revisit if a future source produces a unit that doesn't fit either
dimension cleanly (e.g. a record whose authenticity is itself a
matter of degree, not binary) — via a new ADR extending this one's
shape (Immutable Lineage, `docs/adr/0011`), not an edit to this file.

## Source

Owner decision, architect-chat, 2026-09-14/15, made before and
during the `/spec` interview that produced this sprint's `SPEC.md` —
the two-dimension model, its precedent survey, and the Pearl's-ladder
correction lens were decided there and are already reflected in
`SPEC.md`'s Data Model and Pre-Filter Classification sections; this
ADR is the catch-up record `docs/CONSTITUTION.md`'s doc-currency rule
requires, not a new decision.
