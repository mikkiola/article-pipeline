# Strategy Layer Source-Independence (Collector-First) — Specification

## Overview

Extends Strategy Layer (`strategy_layer/`) from single-source
(Brain/Claim-Extraction-only) to source-independent, via an
Anti-Corruption-Layer-style Pydantic v2 input contract, with Collector
as the first real non-Brain source this sprint. Replaces the single
`verified/disputed/unverifiable/pending` status with two independent
verification dimensions (`integrity_status`, `corroboration_status`).
Routes Collector's data through Strategy Layer instead of bypassing it
directly to Author, for both LinkedIn (rewiring an existing entry
point) and Habr (a new entry point). Brain's own adapter is explicitly
deferred past this sprint — the contract is designed with Brain's
shape in view, but only Collector's adapter is built and wired.

Sprint boundary (owner-confirmed): "publication working" means Author
produces evidence-enriched, publication-ready Markdown drafts, posted
manually. Real automated posting (Platform Adapter) is out of scope.

## Goals

- [ ] Define the two-dimension canonical Pydantic contract
      (`integrity_status` + `corroboration_status`), replacing the old
      single-status Claim/Evidence pair shape.
- [ ] Build Collector's adapter, including a real (not static)
      integrity check.
- [ ] Update Strategy Layer's pre-filter classification table and gate
      condition to key off both dimensions.
- [ ] Route Collector's data through Strategy Layer for both LinkedIn
      (rewired) and Habr (new entry point) — remove the old direct
      bypass once the new path is confirmed working.
- [ ] Add CI enforcement: an import-linter forbidden-import contract, a
      grep-based path-hardcoding lint (import-linter cannot police
      hardcoded path strings), and a synthetic alien-source contract
      test.
- [ ] Write two ADRs (two-dimension verification model; broader
      source-independence/ACL architecture).
- [ ] Restate R6, ratify R8, in wording compatible with the
      two-dimension model.

## Restated/Ratified Requirements (owner-confirmed, this interview)

**R6 (restated — corrects pre-two-dimension-model wording, not a
silent reinterpretation):** Every published piece must contain a
minimum of 1 unit with `integrity_status=valid`, AND if the piece
includes any unit that makes a falsifiable assertion
(`corroboration_status` applicable, i.e. not `not_applicable`), that
assertion must be corroborated — not `unsubstantiated` or `pending`.
No partial/disclosed-unverified fallback for assertions specifically.
This lets Collector-only drafts (all units `corroboration_status=
not_applicable`) satisfy R6 on integrity alone, since they contain no
disputable assertion to begin with.

**R8 (ratified, restated in two-dimension terms):** Every unit with
`corroboration_status=corroborated` must have non-empty `source_url`
and `license` on its corroborating evidence, before it can be marked
`corroborated`. Only constrains units that carry an applicable
`corroboration_status` — no tension with `not_applicable` units, unlike
R6. Enforced structurally by the Pydantic contract (see Data Model).

R1-R5, R7 apply as previously stated (source-agnostic input contract;
evidence-gathering decoupled from source; Author source-agnostic;
adding a source touches only its own adapter; full GitHub-Actions
automation; Habr native-Russian-text quality) — not re-litigated this
interview; R7's actual gap (story_builder.py's body text is still
English per ADR-0043's known limitation) is unchanged by this task and
out of scope here.

## Architecture

**Pattern:** Anti-Corruption Layer / Ports-and-Adapters (owner-approved
2026-09-14, 4-AI consensus). Strategy Layer defines its own inbound
Pydantic contract; each source gets its own adapter translating into
that contract. Strategy Layer's core decision logic (pre-filter, gate,
framing, verdict assembly) does not read source-specific fields
directly.

**Contract technology:** Pydantic v2, `model_config =
ConfigDict(extra="forbid", frozen=True)` — current API confirmed via
live search this session (not from cached knowledge): [Configuration |
Pydantic Docs](https://docs.pydantic.dev/latest/api/config/). This
repo already has Pydantic 2.13.4 installed; no `pyproject.toml`/
`setup.cfg` exists yet — this task creates the repo's first Python
packaging config file (needed for import-linter's config section).

**Two-dimension verification model** (owner decision, this interview
— full ADR text already drafted by the owner, filed verbatim as part
of implementation, see ADR section below):

1. `integrity_status` — every unit, every source, no exceptions.
   Answers: is this record authentic/provenanced?
2. `corroboration_status` — only units making a falsifiable assertion.
   `not_applicable` is a first-class value for bare records (e.g.
   Collector's raw telemetry — a commit either happened or it didn't,
   nothing to corroborate).

A derived conclusion synthesized from raw records (e.g. "activity
increased this week") does not automatically inherit its source
records' statuses — recorded as a design principle for future
implementers; derived-claim synthesis is explicitly **not** built this
sprint (Collector's raw telemetry passes through as individual
records, unsynthesized).

## Data Model — Canonical Input Contract

```python
# strategy_layer/contract.py

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class CanonicalUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str
    source: Literal["brain", "collector"]  # extensible; new sources add a value here, not a new field
    created_at: datetime

    integrity_status: Literal["valid", "invalid"]
    integrity_check_method: str  # e.g. "commit_count_reconciliation" — labels *what kind* of check ran, not a claim of full provenance

    corroboration_status: Literal[
        "corroborated", "disputed", "unsubstantiated", "pending", "not_applicable"
    ]
    assertion_text: str | None  # the falsifiable claim being made; required iff corroboration_status != "not_applicable"

    source_url: str | None = None  # required non-empty when corroboration_status == "corroborated" (R8)
    license: str | None = None     # required non-empty when corroboration_status == "corroborated" (R8)

    metadata: dict[str, Any]  # source-specific pass-through, preserved for Author, never read by Strategy Layer's core logic

    @model_validator(mode="after")
    def _check_assertion_and_corroboration_consistency(self) -> "CanonicalUnit":
        if self.corroboration_status == "not_applicable":
            if self.assertion_text is not None:
                raise ValueError("assertion_text must be null when corroboration_status is not_applicable")
        else:
            if not self.assertion_text:
                raise ValueError(f"assertion_text is required when corroboration_status={self.corroboration_status!r}")
        if self.corroboration_status == "corroborated":
            if not self.source_url or not self.license:
                raise ValueError("source_url and license are required when corroboration_status=corroborated (R8)")
        return self
```

**Design notes:**
- `unit_id` generalizes `claim_id` at the contract-input level (a
  Brain Claim or a Collector telemetry record are both "units"). The
  verdict *output* schema (`claim_treatments`) keeps the field name
  `claim_id` unchanged — see Output Schema below — to avoid
  gratuitous churn in Author-facing output and existing
  `framing.py`/`write_verdict.py` code, which don't need to change.
- No separate join step at the Strategy Layer boundary. The old
  `join_claims_and_evidence()` (joining Claim + Evidence 1:1 on
  `claim_id`, raising on a missing match or null `context`) is
  **removed from `pre_filter.py` entirely**. Each adapter is now
  responsible for producing one complete, valid `CanonicalUnit` per
  meaningful raw record — Pydantic's own construction-time validation
  (`extra="forbid"`, required fields, the `model_validator` above)
  *is* the input-validation gate. An adapter that cannot produce a
  complete unit from a raw record raises before Strategy Layer ever
  sees it — this generalizes the old "missing input data = pipeline-
  ordering error, refuse the whole run" principle to the ACL boundary,
  which is the architecturally correct place for it under this
  pattern (validation happens at the boundary, not inside the core).
- `context` (the old Claim/Evidence field, tags/wiki_links from the
  Context layer) is Brain-specific and does not generalize to
  Collector. It becomes part of `metadata` for Brain's future adapter,
  not a top-level contract field.
- Collector's `metadata` carries whatever's useful for Author
  downstream (e.g. `commit_messages`, `diffstat`, `per_repo`) — never
  read by `pre_filter.py`/`framing.py`/`write_verdict.py`.

## Collector's Integrity Check (owner decision, this interview)

**Finding, confirmed live this session:** Collector's data (both
`daily_brief_*.json` and `manifest_*.json`) contains **no commit
hashes anywhere** — `per_repo` entries are `{name, commit_count,
diffstat, files_touched}`; `manifest`'s `repos` entries are `{name,
branch, commit_count, counts}`. A hash-based provenance check is not
buildable from this data without first adding a hash field to
Collector's own data model — explicitly out of this sprint's scope.

**Chosen check — repo+branch existence AND commit_count
reconciliation:** for each Collector record, verify (a) the named repo
exists as a local checkout and the named branch exists in it (`git
rev-parse --verify <branch>`), and (b) `git rev-list --count` for the
reported window roughly matches the reported `commit_count`. Labeled
in the contract as `integrity_check_method="commit_count_
reconciliation"` — explicitly not a claim of full cryptographic
provenance, a single-metric reconciliation check with bounded
coverage, stated plainly so a future reader doesn't mistake it for
more than it is.

## Pre-Filter Classification (replaces the old single-status table)

| `integrity_status` | `corroboration_status` | `pre_filter_classification` |
|---|---|---|
| `invalid` | *(any)* | `exclude` — integrity is a hard floor, checked first, overrides everything else |
| `valid` | `corroborated` | `include` |
| `valid` | `not_applicable` | `include` — an authentic raw fact with nothing to dispute stands on its own (matches restated R6) |
| `valid` | `disputed` | `exclude` (override available, same mechanism as before) |
| `valid` | `unsubstantiated` | `exclude` |
| `valid` | `pending` | `exclude` |

`classify_pair()`/`classify_unit()`'s function signature changes to
take one `CanonicalUnit` instead of a `(claim, evidence)` dict pair —
its output shape (`{"claim_id", "pre_filter_classification",
"reason"}`) is unchanged, so `framing.py` and `write_verdict.py`
require **no changes** to their own APIs.

## Gate Condition (redefined — owner decision, this interview)

Old: `status="gated"` when every pair's Evidence `status ==
"unverifiable"`. **New: `status="gated"` when zero units in the run
classify `include`** — generalizes "nothing survived the filter" and
works identically whether the run is Collector-only, Brain-only, or
mixed. `gates` object's key renamed from `all_claims_unverifiable` to
`zero_included_units` — **a real output-schema change, flagged
explicitly** per the owner's instruction not to silently absorb such
changes.

## Migration Sequence

1. **Wrap current input as `CanonicalUnit`, confirm existing tests
   still pass — with explicitly flagged exceptions** (see Test Plan
   below; not literally zero test changes, since the owner
   pre-approved the two-dimension shape as the one deliberate change
   to pre-filter's decision logic).
2. **Build Collector's adapter** — `strategy_layer/adapters/
   collector.py`. Reads `manifest_*.json`/`daily_brief_*.json`,
   performs the real integrity check above, produces `list[
   CanonicalUnit]` with `corroboration_status="not_applicable"` for
   every unit (no derived-claim synthesis this sprint).
3. **Route Collector's data through Strategy Layer** for both
   channels:
   - **LinkedIn:** `author/linkedin_verdict_reader.py` (new) — reads
     Strategy Layer's verdict, produces a `daily_brief`-shaped (or
     equivalent) object that `daily_linkedin_author.py`'s existing
     `_build_fact_prompt`/`_build_idea_fallback_prompt` consume
     **unchanged**. `daily_linkedin_author.py`'s own
     `default_daily_brief_path()`/direct `daily_brief_*.json` read is
     removed (step 4) once this path is confirmed working.
   - **Habr (new):** `author/habr_verdict_to_story.py` (new) — builds
     a `CanonicalStory` **directly from the verdict's single included
     claim** (multi-claim synthesis explicitly deferred — this
     sprint's Habr entry point handles exactly one included claim per
     run; more than one is a refusal, clearly flagged, not silently
     mangled). **Does not call `story_builder.py`'s `build_story()`**
     (reads Collector-manifest-specific `commit_fact`/`class_fact` —
     wrong input shape for a verdict). A new, self-contained Habr
     entry point script (not `generate_drafts.py`, which stays
     untouched) drives this — it does **not** reuse
     `channel_author.py`'s `write_draft()` either, since that
     function hardcodes a Collector-specific title
     (`"Как Collector (O1) считает..."`) internally with no override
     parameter; the new entry point has its own minimal, non-
     source-specific rendering, reusing only `channel_profiles.HABR_RU`
     (headings/structure_hint) and the `story_builder.CanonicalStory`
     dataclass definition. `channel_author.py`'s existing title stays
     unedited — it's still used by the untouched `generate_drafts.py`
     path; not this task's file to own.
4. **Remove the old direct bypass** in `daily_linkedin_author.py` once
   step 3's new path is confirmed working (real run against real
   Collector data, not just synthetic tests).
5. **CI enforcement — three mechanisms, not one:**
   - **import-linter** (new `pyproject.toml`, `[tool.importlinter]`
     section): a `forbidden` contract — `source_modules =
     ["strategy_layer"]`, `forbidden_modules = ["claim_extraction",
     "context_layer", "evidence_package", "author.source_adapter"]`
     (symmetric enforcement from day one, covering both the deferred
     Brain chain and Collector-specific coupling, per owner decision).
     Confirmed current config syntax via live search:
     [import-linter docs](https://import-linter.readthedocs.io/en/stable/).
   - **Grep-based path-hardcoding lint** (new script, e.g.
     `scripts/check-strategy-layer-boundary.sh`, same precedent as
     the existing `scripts/check-adr-citation.sh`): fails CI if
     `strategy_layer/pre_filter.py`, `framing.py`, or
     `write_verdict.py` contain literal strings like `collector/data`,
     `daily_brief_`, `manifest_`, `claim_extraction/output` — import-
     linter cannot catch hardcoded path strings (only real Python
     `import` statements), so this closes that specific gap.
   - **Synthetic alien-source contract test**
     (`strategy_layer/test_alien_source_contract.py`): constructs a
     `CanonicalUnit` with `source` extended to include a fabricated
     `"source_x"` value (or, if `Literal` strictness is kept
     symmetric, a structurally valid but semantically alien
     `unit_id`/`metadata` combination under `source="collector"`) and
     confirms `pre_filter.py`/`framing.py`/`write_verdict.py` process
     it with no special-casing — proves genericity by construction.
6. **Two ADRs**, both filed in `docs/adr/` with the next available
   numbers:
   - **Two-dimension verification model** — the owner's own draft,
     filed verbatim (Context/Decision/Rationale/Precedent/
     Consequences as provided in this interview), scoped specifically
     to the `integrity_status`/`corroboration_status` split.
   - **Source-independence / ACL architecture** — a second, separate
     ADR covering the broader decision (Anti-Corruption-Layer pattern,
     Pydantic v2 as contract technology, adapter-per-source,
     import-linter + grep-lint + contract-test enforcement), per the
     2026-09-14 architectural consensus. Distinct decision from the
     two-dimension model even though both land in this sprint.

## Output Schema (verdict — unchanged field names except `gates`)

```json
{
  "run_id": "string",
  "created_at": "ISO8601 string",
  "status": "normal | gated",
  "gates": {
    "zero_included_units": "boolean"
  },
  "claim_treatments": [
    {
      "claim_id": "string",
      "pre_filter_classification": "include | exclude",
      "final_classification": "include | exclude",
      "framing": "string | null",
      "reason": "string"
    }
  ],
  "overrides": [ "...unchanged..." ]
}
```

Only change from the existing (already-implemented) schema: `gates`'s
key, `all_claims_unverifiable` → `zero_included_units`. Everything
else in `write_verdict.py`/`framing.py` is unaffected.

## Functional Requirements

1. Every raw record an adapter processes either becomes a complete,
   valid `CanonicalUnit` (Pydantic-validated at construction) or the
   adapter raises — no partial/malformed unit ever reaches
   `pre_filter.py`.
2. Pre-filter classification is computed per the two-dimension table
   above, before any Claude Code judgment call — unchanged principle,
   changed table.
3. Gate: `status="gated"` / `gates.zero_included_units=true` iff zero
   units in the run classify `include` after pre-filter (before
   override).
4. Claude Code framing pass and override mechanism: unchanged from the
   existing, already-implemented `framing.py` — no behavior change.
5. Collector's adapter performs the real integrity check (repo+branch
   existence + commit_count reconciliation) for every unit it
   produces; `corroboration_status="not_applicable"` for all Collector
   units this sprint (no derived-claim synthesis).
6. LinkedIn and Habr both consume Strategy Layer's verdict, not
   Collector's raw files directly, once step 4 of the migration
   sequence completes.
7. CI blocks a merge if: (a) `strategy_layer/` imports a forbidden
   module (import-linter), (b) `strategy_layer/`'s core files contain
   a hardcoded source-specific path string (grep-lint), or (c) the
   alien-source contract test fails.

## Non-Functional Requirements

1. **TDD applies to the gate-check logic and the Collector adapter's
   integrity check** — both are "does this actually trigger under
   specific conditions" mechanisms per `docs/CONSTITUTION.md`'s TDD
   rule, same precedent as the original gate-check's M2. Write RED
   tests first (gate fires at zero-included, doesn't fire otherwise;
   integrity check fails on a nonexistent repo/branch, fails on a
   commit_count mismatch beyond tolerance, passes on a real match),
   then implement to GREEN, two distinguishable commits.
2. TDD is not required for the classification table itself (a direct,
   static lookup) or for the Habr/LinkedIn glue modules
   (`linkedin_verdict_reader.py`, `habr_verdict_to_story.py`) — plain
   data transformation, cheaply verified by inspection and a real-data
   run, same reasoning the original SPEC applied to the pre-filter
   table.
3. Immutable Lineage continues to apply to verdict output files —
   unchanged, already implemented in `write_verdict.py`.

## Declarative Derivation-Kind Classification for Framing Text (extension, 2026-09-15)

**Why, and why not deferred to BACKLOG:** two gaps were confirmed by
direct code read before this extension was added: (1) framing text's
output language is unconstrained anywhere in the pipeline — the one
real framing string on disk
(`strategy_layer/output/verdict_20260828T211939.json`) is English,
purely incidentally; (2) nothing re-evaluates framing text against the
underlying unit's actual `corroboration_status` — a `not_applicable`
unit (bare Collector telemetry) can get framing text attached that
reads as an evaluative or causal claim, with nothing distinguishing
that from a bare, undisputed fact. Gap 2 is the same "don't let a
status claim more verification than actually happened" principle the
two-dimension model was built around, recurring one layer downstream
(derivation/framing, not raw ingestion) — fixed directly, not deferred.

**Mechanism — declarative, checked by a static rule table, no LLM
call.** Framing text in this pipeline is never human-typed — it is
produced entirely by an automated process (`decide_framing()`'s
interactive seam, or future deterministic code). That same producing
step must emit two additional fields alongside the framing text
itself, at the moment it's created:

- **`derivation_kind`** — one of `restatement` / `aggregation` /
  `evaluation` / `causal_claim` (see
  `strategy_layer/derivation_kind.py`'s module docstring for full
  definitions).
- **`source_status_snapshot`** — the framed unit's `integrity_status`
  and `corroboration_status` **as they were at framing time**, a
  snapshot, not a live reference — if the source record is later
  re-evaluated, the framing's snapshot does not silently change.

**Rule table** (implemented, TDD, `strategy_layer/derivation_kind.py`
+ `strategy_layer/test_derivation_kind.py`, 20/20 passing — RED
confirmed via `ModuleNotFoundError` before implementation existed,
GREEN after):

| `derivation_kind` | Warranted when |
|---|---|
| `restatement` | Always — adds nothing beyond what the source record states |
| `aggregation` | `unit_count_in_run > 1` (a single-record run declaring `aggregation` is unwarranted by construction, regardless of status) |
| `evaluation` | `corroboration_status == "corroborated"`, OR a defined, reproducible aggregation rule exists (`has_defined_aggregation_rule=True` — no such rule is defined anywhere this sprint, so `evaluation` from `not_applicable`/`disputed`/`unsubstantiated`/`pending` is unwarranted in practice today) |
| `causal_claim` | Warranted **only** from `corroborated`; unconditionally **unwarranted** from every other status (`not_applicable`, `pending`, `disputed`, `unsubstantiated`) |

**Correction, 2026-09-15 (same day, before M3 wiring):** an earlier
version of this table named only `not_applicable`/`pending` as
unconditionally unwarranted for `causal_claim`, leaving
`disputed`/`unsubstantiated` silently warranted — flagged as an open
question rather than resolved either way. Owner-confirmed correction:
`disputed`/`unsubstantiated` are, if anything, weaker grounds for a
causal claim than `not_applicable`/`pending`, not stronger — a source
external evidence actively contradicts is not a safer basis than one
merely awaiting evidence. `derivation_kind.py`'s `causal_claim` branch
now inverts the check (`warranted` iff `corroboration_status ==
"corroborated"`) instead of maintaining a growing exclusion set.
`test_derivation_kind.py`'s two previously-flagged tests
(`test_causal_claim_warranted_from_disputed/unsubstantiated_per_
literal_spec_flagged_open_question`) were renamed to
`test_causal_claim_unwarranted_from_disputed/unsubstantiated` with
flipped assertions — RED confirmed against the pre-fix implementation
(both failed: `assert True is False`), GREEN confirmed after (20/20,
full `strategy_layer/` suite 51/51).

**On `unwarranted` — refuse, don't silently mangle:** same principle
already used for the Habr multi-claim case. A unit whose declared
`derivation_kind` the rule table marks `unwarranted` does not get
published as if it were warranted — `final_classification` is forced
to `exclude`, `framing` discarded, with `check_derivation_warranted()`'s
own `reason` string attached. **Integration point, not yet wired this
task:** `build_claim_treatment()` (`framing.py`) is where this check
belongs — called after `derivation_kind`/`source_status_snapshot` are
supplied, before returning an `include`d entry. Not implemented in
this task (only the standalone, tested rule-table function was); wiring
belongs to M3's implementation pass.

**Schema location (decided, this extension):** `derivation_kind` and
`source_status_snapshot` are added to each verdict `claim_treatments`
entry (not a separate top-level list, not on `CanonicalUnit` itself)
— chosen because they describe a fact about *this framing event*, not
about the source unit itself (the same unit's `corroboration_status`
can differ between the moment it's framed and any later re-evaluation
— that's the entire reason for a snapshot, not a live reference), and
`claim_treatments` is already where `framing` and `reason` live at the
same granularity. Updated verdict schema:

```json
{
  "claim_treatments": [
    {
      "claim_id": "string",
      "pre_filter_classification": "include | exclude",
      "final_classification": "include | exclude",
      "framing": "string | null",
      "reason": "string",
      "derivation_kind": "restatement | aggregation | evaluation | causal_claim | null",
      "source_status_snapshot": {
        "integrity_status": "valid | invalid",
        "corroboration_status": "corroborated | disputed | unsubstantiated | pending | not_applicable"
      }
    }
  ]
}
```

`derivation_kind`/`source_status_snapshot` are `null`/absent on
entries where framing was never attempted (a bare pre-filter
`exclude` with no override) — present whenever framing was produced,
including the case where the rule table then forces the entry back to
`exclude`.

**Gap 1 fix — framing language (resolved as documentation, not a new
runtime check as the primary mechanism):** `strategy_layer/
framing.py`'s `decide_framing()` docstring now states explicitly that
Habr-bound framing must be written in Russian — an instruction to the
automated producer, per the owner's own framing of the fix
("specifying the requirement to the producer, not policing arbitrary
text after the fact"). **Optional safety net, built this session since
invited:** `strategy_layer/language_check.py`'s `looks_russian()` — a
crude Cyrillic-character-ratio heuristic (TDD, 6/6 passing), explicitly
not a language-quality check, available for the future Habr entry
point (M5) to call before accepting a framing string. Not wired into
any production path yet — M5 doesn't exist.

## Dependency Pinning (this extension)

`pyproject.toml` created (repo's first Python packaging config),
exact versions pinned, not ranges:
- `pydantic==2.13.4` (already installed this session, confirmed via
  `pip3 show pydantic`)
- `import-linter==2.15` (installed this session — latest available per
  `pip3 index versions import-linter`; pulls in `grimp==3.17` as a
  transitive dependency, pinned too)
- `pytest==9.1.1` (already installed, confirmed via `pip3 show pytest`)

`[tool.importlinter]` section added with the `forbidden` contract
already specified in the Migration Sequence above (`strategy_layer`'s
core modules forbidden from importing `claim_extraction`,
`context_layer`, `evidence_package`, `author.source_adapter`) — not
yet run against real code, since `strategy_layer/contract.py` and the
Collector adapter (M1/M3) don't exist yet; the contract's
`source_modules` list already includes `strategy_layer.derivation_kind`.

## Test Plan — existing 25 tests, changes flagged explicitly

**Unaffected, expected to pass unchanged (14 tests):**
- `test_framing.py` (10 tests) — `framing.py`'s public API
  (`build_claim_treatment`, `derive_overrides`) does not change.
- `test_write_verdict.py` (4 tests) — `write_verdict.py`'s
  `build_verdict`/`write_outputs` do not change, except the `gates`
  key rename flows through automatically (verify assertions reference
  the new key name, not a behavior change).

**Requires rewriting (11 tests in `test_pre_filter.py`) — flagged
explicitly, per owner instruction, not silently absorbed:**
- The 4 `test_pre_filter_table[...]` parametrized cases (keyed by
  single `status`) are replaced by cases over the
  `(integrity_status, corroboration_status)` matrix above (6 rows,
  not 4).
- `test_missing_evidence_record_raises_naming_claim_id` and
  `test_missing_context_field_raises_naming_claim_id_and_field` are
  **removed from `test_pre_filter.py`** — the join they tested no
  longer exists there. Equivalent coverage moves to a new
  `test_collector_adapter.py` (adapter-level: a raw Collector record
  missing an expected field fails to construct a `CanonicalUnit`,
  named clearly).
- `test_full_run_mixed_statuses_no_exception_correct_classifications`
  is rewritten for the two-dimension shape.
- The 4 gate tests (`test_gate_fires_when_all_claims_unverifiable`,
  etc.) are rewritten for the "zero included units" condition and the
  renamed `gates` key.

**New tests, this task:**
- `strategy_layer/test_derivation_kind.py` — the declarative
  derivation-kind rule table (20/20 passing, TDD, RED→GREEN confirmed
  this session — see the dedicated section above).
- `strategy_layer/test_language_check.py` — the optional Habr
  Russian-language safety net (6/6 passing, TDD, RED→GREEN confirmed
  this session).
- `strategy_layer/test_contract.py` — `CanonicalUnit` validation:
  `extra="forbid"` rejects unknown fields, `frozen=True` blocks
  mutation, the `model_validator` enforces
  `assertion_text`/`source_url`/`license` consistency rules (R8).
- `strategy_layer/test_collector_adapter.py` — real integrity check
  (TDD, per Non-Functional Requirement 1): repo/branch existence,
  commit_count reconciliation, both RED-before/GREEN-after.
- `strategy_layer/test_alien_source_contract.py` — the synthetic
  alien-source test (migration step 5).
- A regression test for the grep-based lint script itself (confirms
  it actually catches a synthetic hardcoded-path violation — same
  mutation-testing discipline as this project's other lint scripts).
- **Real-data run:** Collector's adapter against real, current
  `manifest_*.json`/`daily_brief_*.json`, through Strategy Layer, to a
  real verdict file, to a real LinkedIn draft (via
  `linkedin_verdict_reader.py`) and a real Habr draft (via
  `habr_verdict_to_story.py` + the new entry point) — not synthetic
  fixtures, matching this project's established validation precedent.

## Out of Scope (explicit)

- REFLECT / Collector weekly-analysis feature.
- Any Brain-side adapter, stub, or Brain-shaped code path.
- `generate_drafts.py` — untouched.
- `story_builder.py`'s existing Collector-vocabulary leak
  (`value`/`explicit_service`/`default_service` literals) and
  `channel_author.py`'s existing hardcoded Collector-specific title —
  both left as-is; they belong to the old, still-live
  `generate_drafts.py` path, not this task's new Habr entry point.
  Filed as a future BACKLOG cleanup item, not fixed here.
- Derived-claim synthesis from raw telemetry (the two-dimension
  model's "a derived conclusion needs its own evidence basis"
  principle is recorded but not implemented).
- Multi-claim synthesis for the Habr entry point (single included
  claim only, this sprint).
- Platform Adapter / real Habr or LinkedIn posting automation.
- Brain `gitlab` remote cleanup — separate BACKLOG item.
- Any `git push`, token revocation, or destructive git operation —
  this task's boundary is `SPEC.md`; no implementation code is written
  here.

## Milestones

- [x] M1 — `strategy_layer/contract.py`: `CanonicalUnit` Pydantic
      model, two-dimension fields, validators.
      verify: `strategy_layer/test_contract.py`
      done-when: extra-field rejection, frozen mutation-block, and all
      `model_validator` consistency rules pass
      done: 2026-09-15, RED (`ModuleNotFoundError`) confirmed before
      implementation, GREEN after — 10/10 passing
- [x] M2 — Rewrite `pre_filter.py`: remove `join_claims_and_evidence`,
      new two-dimension classification table, redefined gate
      condition (`zero_included_units`).
      verify: rewritten `test_pre_filter.py` (TDD for the gate
      specifically, per Non-Functional Requirement 1)
      done-when: RED-before/GREEN-after for the gate condition;
      classification table matches the 6-row matrix exactly
      done: 2026-09-15, RED (11 `AttributeError`s against the old
      dict-based API) confirmed before rewrite, GREEN after — 11/11
      passing. `run_pilot.py` (the pre-existing Brain-chain M5
      validation script, found via the mandatory codebase-wide search
      before this diff — not previously accounted for) calls the old
      API directly; resolved as an ordinary technical decision, not
      migrated: marked stale in its own docstring, kept as a
      historical record (its job — the Brain-chain pilot — is already
      done and recorded; Brain's adapter is deferred past this
      sprint, so there's nothing to migrate it to).
- [x] M3 — `strategy_layer/adapters/collector.py`: real integrity
      check (repo/branch existence + commit_count reconciliation),
      produces `list[CanonicalUnit]`. Also: `derivation_kind`/
      `source_status_snapshot` wired into `build_claim_treatment()`
      (new optional parameters, opt-in — old callers get the
      unchanged 5-key dict shape, new callers get 7 keys; resolves the
      schema-conflict flag from this section's earlier draft without
      needing to touch `test_framing.py`'s original 10 tests).
      verify: `strategy_layer/adapters/test_collector.py` (TDD,
      mocked `subprocess.run`); `test_framing.py`'s new
      `derivation_kind` cases (TDD)
      done-when: RED-before/GREEN-after; real run against current
      Collector data produces valid `CanonicalUnit`s
      done: 2026-09-15, RED confirmed for both (`ModuleNotFoundError`;
      `TypeError: unexpected keyword argument`), GREEN after — 12/12
      and 16/16 respectively. Real run (`strategy_layer/
      run_collector_pilot.py`, throwaway orchestration, same class as
      `run_pilot.py`) against `manifest_2026-09-12.json` produced a
      real verdict (`strategy_layer/output/verdict_20260915T191323
      .json`) with `derivation_kind`/`source_status_snapshot` actually
      populated.

      **Two real findings from the real run, not caught by the mocked
      unit tests:**
      1. A genuine bug: `git`'s `--since=N.days` shorthand resolves
         relative to actual wall-clock "now," not to `--until` —
         combined with an explicit `--until` anchor, this silently
         shifted the reconciliation window forward, undercounting (5
         of 7 repos mismatched, reconciled consistently lower than
         reported). Fixed: both bounds now computed as absolute
         timestamps. Confirmed fixed — after the fix, 5 of 7 repos
         reconcile exactly.
      2. A structural limitation, not a bug, left unresolved
         deliberately: 2 of 7 repos (`collector`, `radar-vault`) still
         mismatch by ±1 after the fix. Traced `collector`'s case to a
         commit (`b89008e`, "weekly Collector EMIT 2026-09-12")
         timestamped exactly at `scan_timestamp` — almost certainly
         the commit that records the manifest file itself, created
         moments after the scan ran but stamped at effectively the
         same instant; date-based `--until` filtering is inclusive at
         that boundary. `radar-vault`'s cause wasn't individually
         traced. Not adjusted to paper over this — the exact-match
         tolerance choice was explicitly owner-confirmed with its own
         stated reasoning; loosening it unilaterally would silently
         override that decision. Flagged here for the owner, not
         resolved.
- [x] M4 — `author/linkedin_verdict_reader.py` +
      `daily_linkedin_author.py`'s old direct-read bypass removed.
      verify: real run, verdict → LinkedIn draft, no `daily_brief_
      *.json` read anywhere in `daily_linkedin_author.py`
      done-when: a real LinkedIn draft is produced from a real
      Strategy Layer verdict, not a direct Collector read
      done: 2026-09-15 (ADR-0045: `author/authoring_context.py`,
      built post-classification directly from `CanonicalUnit` +
      `claim_treatments`, never touching the verdict schema — closes
      the gap that a persisted verdict alone can't carry raw per-repo
      metadata). RED/GREEN confirmed for both `test_authoring_context.py`
      (5/5) and `test_linkedin_verdict_reader.py` (4/4).
      `default_daily_brief_path()` removed from `daily_linkedin_author.py`;
      its CLI now requires an explicit path, no silent Collector-file
      default. Real run (`strategy_layer/run_linkedin_pilot.py`)
      against real `daily_brief_2026-09-14.json`: real Russian commit-
      message text reached the constructed prompt's `commit_messages`
      field, confirmed by literal output; the live `gh repo view` L2
      check also ran for real.
- [x] M5 — `author/habr_verdict_to_story.py` + new Habr entry point
      script (`author/habr_weekly_author.py`, manifest/weekly-sourced
      — SPEC.md never pinned this cadence explicitly; chosen to match
      `generate_drafts.py`'s existing Habr precedent).
      verify: real run, verdict (single included claim) → Habr RU
      draft
      done-when: a real Habr draft is produced from a real Strategy
      Layer verdict; a run with >1 included claim refuses clearly,
      does not silently mangle output
      done: 2026-09-15/16, in two passes. First pass built exactly
      this single-claim design (RED/GREEN, `test_habr_verdict_to_story.py`
      6/6) — its own real end-to-end run against `manifest_2026-09-12
      .json` then showed 5 included claims is what a typical real week
      actually produces, not an edge case, and the single-claim design
      correctly refused (`MultiClaimNotSupportedError`) rather than
      fabricating a story — meaning Habr publication did not work
      against real data at all. **Superseded same-session by
      ADR-0046** (multi-claim digest: `HabrDigest`/`HabrDigestSection`,
      structural juxtaposition of already-vetted per-claim framing
      text under one shared Russian title, no LLM, per-claim
      `looks_russian()` check with partial exclusion rather than
      all-or-nothing refusal) — this `done-when` text itself describes
      the now-superseded single-claim behavior; see ADR-0046 for the
      accepted design. RED/GREEN confirmed for the rebuilt
      `test_habr_verdict_to_story.py` (8/8) and `test_habr_weekly_author.py`
      (5/5). Re-run against the same real `manifest_2026-09-12.json`
      data: all 5 real claims represented (`HabrDigest sections: 5 of
      5 included contexts`), zero truncation, full Russian text
      confirmed throughout.
- [x] M6 — CI enforcement: import-linter contract (`pyproject.toml`),
      grep-based path-hardcoding lint script, alien-source contract
      test, wired into a new GitHub Actions workflow.
      verify: `test_alien_source_contract.py`; lint-script regression
      test; a real PR touching `strategy_layer/` triggers the new
      workflow
      done-when: all three mechanisms independently confirmed to
      catch a synthetic violation (mutation-tested, same discipline as
      this project's other lint scripts)
      done: 2026-09-16. Blocker resolved first: `strategy_layer/__init__.py`
      and `author/__init__.py` added — mandatory codebase-wide search
      (grep for every `sys.path.insert()` call, 29 found across
      `strategy_layer/`+`author/`, zero dotted-package imports found
      anywhere) confirmed no existing bare-import call site breaks;
      131/131 reconfirmed unaffected immediately after. Two real
      import-linter config gaps found only once run for real (never
      run before this milestone): `include_external_packages = true`
      required for external `forbidden_modules`; `author.source_adapter`
      needed `root_packages = ["strategy_layer", "author"]` (not a
      bare `root_package` string) since a subpackage of a purely
      external package isn't a valid forbidden-module reference. All
      three mechanisms independently mutation-tested: import-linter
      (a real `import claim_extraction` planted in `pre_filter.py` —
      contract went `BROKEN`, exit 1, exact line cited; reverted —
      `KEPT`, exit 0); grep-lint
      (`scripts/check-strategy-layer-boundary.sh` +
      `scripts/test-strategy-layer-boundary-check.sh`, 6 cases, each of
      SPEC.md's 4 named strings independently confirmed blocking, plus
      a scope-boundary case; RED confirmed by breaking the check
      script — `unbound variable`, test caught it — GREEN after
      restore); alien-source contract test
      (`strategy_layer/test_alien_source_contract.py`, 6/6, a
      structurally-valid-but-alien `source="collector"` unit per
      SPEC.md's own fallback design since the `source` Literal stayed
      strict; RED confirmed by planting source-specific special-casing
      in `pre_filter.py` — 5/6 failed — GREEN after revert).
      `.github/workflows/strategy-layer-boundary-ci.yml` wired,
      Python 3.14 (matching `pyproject.toml`'s `requires-python`, not
      the older workflows' 3.11), all four steps dry-run locally in
      workflow order. **Not verified**: the workflow actually firing on
      a real GitHub PR — requires a real push, out of scope for a
      working-tree-only session; first real PR touching
      `strategy_layer/` after this lands is the actual confirmation.
- [x] M7 — Two ADRs filed in `docs/adr/` with real numbers.
      verify: `scripts/check_adr_numbering.py` (existing CI check)
      done-when: both ADRs pass numbering/structural validation
      done: 2026-09-16. Owner confirmed, resolving this milestone's own
      prior open question: ADR-0045/0046 record different decisions
      (post-classification authoring context; Habr multi-claim digest)
      and do not satisfy M7 by extension — the originally-scoped pair
      is filed separately as ADR-0047 (Two-Dimension Verification
      Model) and ADR-0048 (Source-Independence via Anti-Corruption
      Layer Architecture), both Accepted.
      `scripts/check_adr_numbering.py`: `OK: all ADRs in docs/adr
      numbered correctly.` `docs/adr/ADR-INDEX.md` regenerated (48
      ADRs indexed).

**Handoff, 2026-09-16 (sprint complete).** M1–M7 are all done — every
milestone's own `done:` entry above carries its literal RED/GREEN
test output and, where applicable, real-run evidence. Full
`strategy_layer/` + `author/` suite: 137/137 (131 from M1–M5 plus 6
new alien-source contract tests, M6). All work committed to git this
session, split along milestone boundaries — see git log for the exact
commit SHAs; nothing pushed to `origin`, per this project's
unconditional sensitive-ops rule (pushing is a manual, owner-only
action). Out of scope for this sprint and unchanged:
`story_builder.py`/`channel_author.py`'s Collector-vocabulary leak
(filed as a future cleanup item, not fixed), derived-claim synthesis
from raw telemetry, Brain's own adapter (deferred past this sprint,
per the Out of Scope section above).

## Open Questions / Decisions Needed

None blocking implementation of M1-M7 above — every fork raised by
`pre-spec`'s sensor run and by this interview itself (R6/R8 wording,
integrity-check method, Habr's verdict-to-story bridge, N-claims-to-
5-slots handling, module naming/location, gate redefinition,
import-linter scope, path-hardcoding enforcement) was resolved
directly by the owner in this interview and is recorded in the
relevant section above.

One deferred, non-blocking note for a future session: the vocabulary-
leak cleanup in `story_builder.py`/`channel_author.py` (Out of Scope,
above) — not this SPEC's scope to resolve, flagged only so a future
session doesn't assume it was overlooked. A second: multi-claim
synthesis for Habr, deferred by explicit owner choice this interview,
will need its own design once a real run produces more than one
included claim.

**Resolved, 2026-09-15 (was open in an earlier version of this
section):** whether `causal_claim` should also be unconditionally
unwarranted from `disputed`/`unsubstantiated` sources — yes, confirmed
by the owner same-day. See the Rule Table section above for the
correction and its RED→GREEN confirmation. No longer an open question.

## Source

`/spec` interview, 2026-09-15, following two prior sessions in this
same thread: (1) a fresh-state verification pass re-confirming every
factual claim from a 2026-09-14 gap-analysis session against live
code/git history, and (2) a `pre-spec` pass (`finding-unknowns` +
`phrase-decomposer`) that surfaced two BLOCKING findings — verification
semantics for Collector's telemetry (no counterpart to Brain's
Claim/Evidence status vocabulary existed), and the absence of any real
Habr/LinkedIn posting mechanism anywhere in the codebase. Both resolved
by the owner before this interview began (two-dimension model;
sprint-scope boundary at manual-post-ready drafts). This interview
itself surfaced and resolved several further forks not caught by
pre-spec: R6/R8's wording under the two-dimension model, Collector's
integrity-check method (no commit hashes exist in Collector's actual
data — discovered live, this interview), the verdict-to-CanonicalStory
structural mismatch for Habr (resolved after reading `channel_author.py`
live and finding it does zero content-aware processing), and the
two-ADR split (two-dimension model vs. broader ACL architecture, as
distinct decisions). Current Pydantic v2 (`ConfigDict(extra="forbid",
frozen=True)`) and import-linter (`[tool.importlinter]`, `forbidden`
contract type) config syntax confirmed via live web search this
session, not cached knowledge — see citations in the Architecture
section above.
