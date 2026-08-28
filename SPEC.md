# Strategy Layer (Phase 3) — Specification

## Overview

Strategy Layer reads a run's Claims (each already carrying its own
`context` field from the Context/causal-structure layer and exactly one
Evidence record from Evidence Package) and produces one verdict object
per run — a structured "config" (per `docs/adr/0007-strategy-layer-
separate-from-platform-adapter.md`) that Author will later consume to
write the actual article. This SPEC covers Strategy Layer only: its
input contract, its decision logic, and its output contract to Author.
Author's own implementation, Quality Gate, Multi-Source Claim Layer,
Trust & Safety Gate, Publication Control, monetization requirements, and
Loop Engineering are all explicitly out of scope (see `docs/BACKLOG.md`'s
`[B-047]` for the last of these — deferred on the same reasoning this
SPEC also applies).

## Goals

- [ ] Define Strategy Layer's exact input contract (what fields it reads
      from Claim/context/Evidence — verified against real code, not
      assumed).
- [ ] Define the Hybrid execution model's split between a deterministic
      pre-filter and Claude Code's judgment, including the override
      mechanism and its logging.
- [ ] Define the one v1 gate condition and its trigger logic precisely
      enough to TDD.
- [ ] Define the verdict's exact output schema — Strategy Layer's
      contract to Author.
- [ ] Define missing-input-data handling (pipeline-ordering error, not a
      silent category).
- [ ] Define the Test Plan / Validation approach for v1.

## Design Philosophy (owner decision, this interview)

**Simple design, built from real data — not the uncommitted architect-
chat proposal.** The prior discussion (Toulmin argumentation model +
Pearl's causal hierarchy + Hard Gates evaluated before scoring + a
Worldview Contract as small YAML) is **not adopted for v1**. Reasoning,
in the owner's own words: zero production code exists for Strategy Layer
today, and the full proposal was never validated against real data —
building it now would repeat the same mistake found earlier this session
with `docs/ROADMAP.md`'s dependency diagram (a design accepted on faith,
never checked against reality). Deferred on the same basis as Loop
Engineering (`docs/BACKLOG.md`'s `[B-047]`) — revisit once real runs
produce data showing the richer structure is actually needed.

**This is a sequencing choice, not a rejection of the ideas.** If, while
implementing the simple version, a pattern clearly maps to Toulmin's
claim/grounds/warrant structure, or to a Hard-Gate-shaped check (a
condition that should block scoring outright, not just lower it), that
pattern must be named explicitly in code/comments as a natural extension
point — the vocabulary is not forced in now, but the design must not be
flattened to avoid noticing it either. The override-logging mechanism
below (see Execution Model) is one concrete place this is expected to
surface first.

## Input Contract (verified against real code this session)

**Claim** (`claim_extraction/build_pilot_output.py`, Implemented):
```
{
  "claim_id": str,
  "extracted_at": str (ISO8601),
  "atom_path": str,
  "status": str,
  "confidence": <type not locally enumerated in claim_extraction;
                 treat as opaque signal, see Data Model note below>,
  "category": str,
  "reason": str,
  "context": {                       # added by Context layer, below
    "tags": list,
    "wiki_links": list
  }
}
```

**Context/causal-structure layer** (`context_layer/enrich.py`,
Implemented — M1-M5): `extract_context(atom_path)` returns
`{"tags": [...], "wiki_links": [...]}`, merged into the Claim record as
its `context` field. Confirmed by direct read: no richer "causal
structure" exists in production code today — the `experiment_*.json`
files in `context_layer/` are research artifacts (run_id/design/rubric/
runs/cross_run_finding), not a stable per-Claim output shape. Any
"causal hierarchy" concept is out of scope for v1 per the Design
Philosophy above.

**Evidence Package** (`evidence_package/write_evidence.py` +
`evidence_package/driver.py`, Implemented): exactly one Evidence record
per Claim — confirmed via `driver.py`'s `run_searches()`, which iterates
`for claim in claims` and emits one record per iteration; no skip logic
exists that would leave a Claim without a corresponding record once
Evidence Package has run for it.
```
{
  "evidence_id": str,
  "run_id": str,
  "created_at": str (ISO8601),
  "claim_id": str,
  "status": "verified" | "disputed" | "unverifiable" | "pending",
  "searched_at": str,
  "search_query": str,
  "requests_used": int,
  "source_url": str | null,
  "source_title": str | null,
  "license": str | null,
  "note": str | null
}
```

**Strategy Layer's actual input, per run:** a list of `(Claim, Evidence)`
pairs, one pair per Claim, joined on `claim_id`. Both halves of every
pair must be present — see Missing Input Data below.

## Missing Input Data (owner decision, this interview)

If a Claim in scope for this run has no matching Evidence record, or no
`context` field, this is **not** a legitimate Evidence Package/Context
layer outcome — Evidence Package is confirmed strictly 1:1 with Claims
(no skip logic), and Context layer only ever adds the `context` field,
never omits it as a result. Either gap means Strategy Layer is being run
out of order, before an upstream step has processed that Claim.

**Treatment:** this is a run-level pipeline-ordering error, not a silent
per-Claim category. Strategy Layer must refuse to proceed for the
affected run (not just skip the affected Claim) and report which
Claim(s) and which missing field caused the refusal. This must not be
folded into a normal-looking verdict — consistent with the v1 gate's own
principle (Functional Requirements below): incomplete or out-of-order
input must never quietly produce a normal-shaped output.

## Execution Model — Hybrid (owner decision, this interview)

Two stages, run in sequence per invocation:

**Stage 1 — deterministic pre-filter.** Pure code, no LLM call. For each
`(Claim, Evidence)` pair, computes `pre_filter_classification` from
Evidence's `status` field:

| Evidence `status` | `pre_filter_classification` | Rationale |
|---|---|---|
| `verified` | `include` | Accuracy established. |
| `disputed` | `exclude` | Per `docs/adr/0003-honest-packaging-vs-honest-content.md`'s non-negotiable accuracy floor ("packaging never trades against accuracy") — a contested fact is not an established one by default. Override available (below) for a case Claude Code judges is honestly reportable as a live dispute. |
| `unverifiable` | `exclude` | No evidence found; accuracy not established. |
| `pending` | `exclude` | Not yet resolved; do not publish prematurely. |

Stage 1 also evaluates the v1 gate condition (Functional Requirements
below) over the whole run's Evidence statuses.

**Stage 2 — Claude Code judgment (interactive).** For every Claim with
`pre_filter_classification == "include"`, Claude Code decides the actual
framing/voice for that Claim (per ADR-0007: this is exactly the
"framing/hook/voice" decision Strategy Layer owns). Claude Code also
holds **override right**: it may set a Claim's `final_classification`
differently from `pre_filter_classification` in either direction,
**only** if it records a `reason` for the override — this is mandatory,
not optional, whenever `final_classification != pre_filter_classification`.

**Why override right exists** (owner's own reasoning, recorded
verbatim because it shapes the schema below): without it, Hybrid
degrades into "deterministic layer decides everything except prose
framing" — the pre-filter alone would drive every include/exclude
decision, leaving Claude Code as a text generator, not a decision-maker,
defeating the reason Hybrid was chosen over a pure deterministic model.

**Why overrides are logged plainly, not analyzed:** if, over real runs,
Claude Code repeatedly overrides the same kind of case (e.g. unverifiable
Claims with strong corroborating `context.wiki_links`), that pattern is
a real signal worth noticing later — possibly pointing toward a
Toulmin-shaped (claim + grounds) structure being the natural fit for
that case. This is **not** the reason override right exists; it is a
welcome side effect if it happens. The override log must not be designed
around anticipating this pattern — just record `claim_id`,
`pre_filter_classification`, `final_classification`, and `reason`,
plainly, so the pattern is visible later if it exists, without building
anything speculative now.

## Functional Requirements

1. **Input validation.** Every Claim in the run must have exactly one
   matching Evidence record and a non-null `context` field before any
   classification happens. A gap triggers the Missing Input Data
   treatment above — the run refuses to proceed, not silently continues.
2. **Deterministic pre-filter.** Every `(Claim, Evidence)` pair gets a
   `pre_filter_classification` per the table above, computed before any
   Claude Code judgment call.
3. **The one v1 gate — all-Claims-unverifiable.** If every Claim in this
   run has Evidence `status == "unverifiable"` (i.e., no `verified` and
   no `disputed` Claims exist in this run — `pending` alone does not
   satisfy this condition, since `pending` means "not yet resolved,"
   a materially different state from "resolved as unverifiable"), the
   verdict's top-level `status` field must be `"gated"`, and
   `gates.all_claims_unverifiable` must be `true`. The verdict must not
   otherwise look like a normal, ungated verdict when this fires.

   **Chosen over the alternative condition considered** ("zero
   includable Claims after Hybrid filtering blocks the verdict
   entirely") because this is the one condition already observed on
   100% of real runs to date — all 5 live Evidence Package runs so far
   resulted in `unverifiable` (`docs/ARCHITECTURE.md`'s Evidence
   Package Validation column: "5 live Claims tested, 5/5 unverifiable").
   Choosing it means the very first real Strategy Layer run exercises
   the gate meaningfully. The alternative condition is deferred, not
   rejected — a concrete future trigger (real Claims filtered out for
   reasons other than blanket unverifiable evidence) would justify a
   second gate, added then, not guessed at now.
4. **Claude Code framing pass.** For every Claim where
   `pre_filter_classification == "include"` (after any override — see
   below), Claude Code produces a `framing` string: the actual
   framing/voice decision for that Claim, per ADR-0007's scope for
   Strategy Layer.
5. **Override mechanism.** Claude Code may set `final_classification`
   different from `pre_filter_classification` for any Claim, provided a
   `reason` is recorded. Every such Claim also gets an entry in the
   verdict's `overrides` list (see Data Model). A Claim whose
   `final_classification` ends up `"exclude"` (whether by the pre-filter
   or by override) must always carry a non-null `reason` — this is what
   satisfies "excluded Claims recorded with reason."
6. **One verdict object per run**, not one object per Claim and not an
   argument-graph structure — matches ADR-0007's "Strategy Layer outputs
   a config" framing directly (owner decision, this interview).

## Non-Functional Requirements

1. **No new vocabulary in v1.** No field, function, or class name may
   use "Toulmin," "Pearl," "Hard Gate," or "Worldview Contract" — the
   deferred proposal's concepts may be approximated internally (e.g. the
   pre-filter/override split, the gate mechanism) but the terms
   themselves stay out of the codebase until a real, data-backed trigger
   justifies adopting them (Design Philosophy above).
2. **TDD applies to the gate-check logic specifically** (owner-facing
   note, Claude Code's own judgment call per `docs/CONSTITUTION.md`'s
   TDD rule: "the mechanism's entire job is making a judgment call under
   specific conditions... where 'does this actually trigger' is the
   central risk"). Write a test asserting the all-unverifiable condition
   sets `status: "gated"` / `gates.all_claims_unverifiable: true`
   correctly — and that a run with even one `verified` or `disputed`
   Claim does *not* trigger it — confirm RED before the gate-check
   function exists, then implement to GREEN. TDD is not required for the
   Claude Code framing pass itself (a judgment call, not a mechanical
   trigger condition) or for the pre-filter table (a direct, static
   lookup with no conditional trigger logic to get wrong in the same
   way).
3. **Immutable Lineage applies to verdict output files**, same
   convention as Evidence Package's `write_outputs()` — never overwrite
   a previous run's verdict; a `run_id` collision is an error, not a
   silent overwrite.

## Data Model — Verdict Output Schema (Strategy Layer's contract to Author)

```json
{
  "run_id": "string",
  "created_at": "ISO8601 string",
  "status": "normal | gated",
  "gates": {
    "all_claims_unverifiable": "boolean"
  },
  "claim_treatments": [
    {
      "claim_id": "string",
      "pre_filter_classification": "include | exclude",
      "final_classification": "include | exclude",
      "framing": "string | null   — non-null only if final_classification == include",
      "reason": "string   — required always; explains exclude, or the override, or is empty-string-not-allowed for a bare include with no override"
    }
  ],
  "overrides": [
    {
      "claim_id": "string",
      "pre_filter_classification": "include | exclude",
      "final_classification": "include | exclude",
      "reason": "string"
    }
  ]
}
```

**Design notes, stated explicitly per this session's own "verify
compliance" discipline (learned from the ROADMAP.md diagram finding):**
- `overrides` is a **derived index** over `claim_treatments` — every
  entry in it corresponds exactly to a `claim_treatments` entry where
  `final_classification != pre_filter_classification`. It is always
  recomputable from `claim_treatments` and is not independently
  authoritative — kept as its own top-level list purely for the
  visibility the owner asked for (spotting an override pattern later
  without diffing two fields across every entry), not as a second
  source of truth.
- There is **no separate `excluded_claims` list.** "A record of any
  Claim excluded and the reason" (owner's stated requirement) is
  satisfied by `claim_treatments` entries with
  `final_classification == "exclude"`, each carrying a mandatory
  `reason` — a dedicated duplicate list was considered and rejected to
  avoid the single-source-of-truth violation this project has
  specifically flagged elsewhere this session (`docs/BACKLOG.md`'s
  `[B-053]`, ROADMAP.md's dependency diagram going stale independently
  of ARCHITECTURE.md).
- `gates` is an object, not a flat top-level boolean, even though v1
  has exactly one gate — deliberately leaves room for a future gate to
  be added as a new key without a schema-breaking shape change (owner's
  own "space for gate-like checks... even without a full Pearl/Hard-
  Gates model yet").
- `confidence`'s exact type/range is not locally enumerated anywhere in
  `claim_extraction/` (confirmed by grep — no `STATUSES`-style constant
  for it there). It is not used in the v1 pre-filter table (Evidence
  `status` is the sole deterministic driver, per the owner's stated
  priority-ordered reasoning) — available to Claude Code's judgment
  pass as context, not wired into any deterministic rule. If a future
  session finds this field warrants a defined range/enum, that is
  `claim_extraction`'s own scope, not Strategy Layer's, since Strategy
  Layer only consumes the field, it doesn't define it.

## Test Plan

Matches this project's own established validation pattern (Claim
Extraction: "4 immutable pilot runs, manually verified"; Evidence
Package: "5 live Claims tested, 5/5 unverifiable" — both from
`docs/ARCHITECTURE.md`).

1. **Gate-check unit test (TDD, per Non-Functional Requirement 2).**
   Synthetic Evidence-status combinations: all-`unverifiable` → gated;
   one `verified` among otherwise-`unverifiable` → not gated; one
   `disputed` among otherwise-`unverifiable` → not gated; all-`pending`
   → not gated (confirms `pending` alone does not satisfy the
   all-unverifiable condition, per Functional Requirement 3's explicit
   note).
2. **Pre-filter table unit test.** Each of the four Evidence `status`
   values maps to the documented `pre_filter_classification`.
3. **Missing-input-data test.** A Claim with no matching Evidence
   record, and separately a Claim with no `context` field, each cause
   the run to refuse to proceed with a clear report of which Claim/field
   caused it — not a partial verdict, not a crash with an unrelated
   traceback.
4. **Real-data run.** Run Strategy Layer against the same 5 live Claims
   already used for Evidence Package's own pilot (`docs/ARCHITECTURE.md`:
   "5 live Claims tested, 5/5 unverifiable"). Per the owner's own
   reasoning for choosing the v1 gate condition, this run is expected to
   trigger `gates.all_claims_unverifiable: true` — confirming the gate
   fires on the first real invocation, not only in synthetic tests.
5. **Override path, real or synthetic.** At least one case where Claude
   Code's judgment overrides a pre-filter `exclude` (or `include`)
   classification, confirming the override lands correctly in both
   `claim_treatments` and the derived `overrides` list, with a non-null
   `reason` in both places.

## Milestones

- [ ] M1 — Deterministic pre-filter (Stage 1): implement the four-row
      classification table and the input-validation refusal path.
      verify: pytest against the pre-filter table + missing-input-data
      tests (Test Plan items 2-3)
      done-when: all synthetic pre-filter and missing-input cases pass
- [ ] M2 — Gate-check logic (TDD per Non-Functional Requirement 2):
      write the RED test first, then implement to GREEN.
      verify: pytest against Test Plan item 1 (gate-check unit test)
      done-when: RED confirmed before implementation, GREEN after,
      committed as two distinguishable states in the session (per
      docs/CONSTITUTION.md's TDD rule)
- [ ] M3 — Claude Code framing pass + override mechanism (Stage 2):
      interactive judgment call producing `framing` for included Claims,
      with override right and mandatory `reason` logging.
      verify: Test Plan item 5 (override path)
      done-when: at least one real or synthetic override case is
      recorded correctly in both `claim_treatments` and `overrides`
- [ ] M4 — Verdict assembly + Immutable Lineage output writer, matching
      Evidence Package's `write_outputs()` convention (never overwrite a
      prior run; `run_id` collision is an error).
      verify: attempt a second write with a colliding `run_id`, confirm
      it raises rather than overwrites
      done-when: collision test passes
- [ ] M5 — Real-data validation run against the 5 existing live Claims.
      verify: Test Plan item 4
      done-when: the run completes, produces a verdict with
      `status: "gated"` / `gates.all_claims_unverifiable: true`, and the
      output is manually reviewed and confirmed correct (matching this
      project's own "manually verified" precedent for pilot validation)

## Open Questions / Decisions Needed

None blocking implementation of M1-M5 above — every fork raised by
`pre-spec`'s sensor run (adopt-the-full-proposal-or-not; output
cardinality/shape; Hybrid split; v1 gate condition; missing-input-data
handling) was resolved directly by the owner in this interview and is
recorded in the relevant section above, not left open here.

One deferred, non-blocking note for a future session: `confidence`'s
undefined type/range (Data Model, above) — not this SPEC's scope to
resolve, flagged only so a future session doesn't assume it was
overlooked.

## Source

`/spec` interview, 2026-08-28, following `docs/BACKLOG.md`'s `[B-052]`
(explicit owner decision to stop monetization analysis and resume Phase
3) and `docs/ROADMAP.md`'s Current pointer. Preceded by `pre-spec`
routing both `finding-unknowns` and `phrase-decomposer` against the
Strategy Layer problem space (both signal types fired): `finding-unknowns`
found 3 resolved facts (Context layer's real output shape, Evidence
Package's real output shape and 1:1 Claim cardinality, zero prior
grounding for Toulmin/Pearl/Hard-Gates/Worldview-Contract anywhere in
this repo), 1 WARNING (Author's input contract only thinly defined by
ADR-0007), and 1 BLOCKING (adopt-the-proposal-or-not, a genuine
architecture fork with no basis in this repo to prefer one option —
resolved by the owner in this interview, "simpler design" chosen).
`phrase-decomposer` found 1 BLOCKING (the task's own phrase "a decision
(or set of decisions)" admitted 3 architecturally different readings —
resolved by the owner, "one verdict per run" chosen, matching
ADR-0007). All owner decisions recorded verbatim/near-verbatim above,
including stated reasoning, per this project's own "state uncertainty
as uncertainty, cite the actual source" discipline.
