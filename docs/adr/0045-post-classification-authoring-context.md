---
id: ADR-0045
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0045: Post-Classification Authoring Context

## Status

Accepted.

## Context & Constraints

Strategy Layer's source-independence work (this session's `SPEC.md`)
built a Collector adapter (`strategy_layer/adapters/collector.py`, M3)
whose only tested path reads `manifest_<date>.json` (weekly). It has
no path for `daily_brief_<date>.json` (daily) — the file
`daily_linkedin_author.py`'s prompt builders actually need, because
only `daily_brief` carries real commit-message subject text (a flat,
cross-repo `commit_messages` array); `manifest` never carries this
text, by Collector's own design (confirmed by reading
`collector/scripts/daily_brief.py`'s `compute_metrics()` and
`collector/scripts/tier0_scan.py`).

Confirmed by a real generated draft
(`author/output/draft_linkedin_daily_2026-09-03.json`): the LLM's
actual output closely paraphrases specific commit-message text when
it's available in the prompt, not generic activity prose — commit-
message text is load-bearing for output quality, not decoration.

Attempting to wire this through Strategy Layer's existing
verdict/`claim_treatments` schema surfaced a structural conflict: that
schema (`SPEC.md`'s Output Schema section) carries only `claim_id`,
`pre_filter_classification`, `final_classification`, `framing`,
`reason`, `derivation_kind`, `source_status_snapshot` — no raw
per-repo metadata (commit counts, diffstats, file lists, commit
message text). Author's prompt builders need that raw data, not just a
prose `framing` string.

## Decision

A separate `AuthoringContext` object (`author/authoring_context.py`),
built by its own dedicated function (`build_authoring_contexts()`),
directly from a list of `CanonicalUnit` instances that already
classified `include` (cross-referenced against already-computed
`claim_treatments`, never re-running classification logic) — assembled
*after* classification is final, not as part of it.

The verdict/`claim_treatments` schema is not modified to carry this
data. `AuthoringContext` is never passed to or built by anything in
`strategy_layer/`'s classification logic (`pre_filter.py`,
`framing.py`, `write_verdict.py`) — confirmed zero such imports exist
at the time this ADR was accepted (mandatory codebase-wide search,
2026-09-15). `AuthoringContext` itself lives in `author/`, not
`strategy_layer/`, specifically so this is a real package/directory
boundary, not a convention those three files are merely trusted not to
violate.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| **A. Passthrough field on the verdict schema** (e.g. `source_metadata`, `generation_context`, added directly to `claim_treatments`). | Rejected. Considered and rejected by the owner before this task began: it would let classification-stage code read raw source data later — the exact Anti-Corruption-Layer boundary this whole migration exists to enforce. Once such a field exists on the verdict schema, nothing structurally prevents a future change to `pre_filter.py`/`framing.py` from reading it, re-introducing source coupling into the one place this migration was built to keep source-agnostic. |
| **B. External database / claim-check store.** | Rejected. Researched and rejected: the claim-check pattern exists for payloads that exceed messaging-system size limits. This pipeline's daily commit-message payloads are 2-10 KB, well under any such limit. A database adds real infrastructure (a server, a schema, sync, backup) for a problem of this size that it doesn't actually have — this project's own token/cost-consciousness principle (`docs/CONSTITUTION.md`'s "Mechanical verification scope" section cites the same reasoning for a different decision) already rejects exactly this kind of scope mismatch. |
| **C. Chosen — `AuthoringContext`, built post-classification, directly from `CanonicalUnit`, never touching the verdict schema.** | Closes the actual gap (Author needs raw per-repo data the verdict doesn't carry) without weakening the ACL boundary Option A would compromise, and without the infrastructure Option B would add for no real need. The boundary is enforced structurally (a different package, a different call graph) rather than by convention alone. |

## Consequences

- `AuthoringContext` (Pydantic, `extra="forbid"`, matching `CanonicalUnit`'s
  own strictness) exposes: `claim_id`, `framing` (from the matching
  `claim_treatments` entry), `source_type`
  (`"collector_manifest"` | `"collector_daily_brief"`), `repo`,
  `commit_count`, and source-specific raw material — `diffstat`/
  `files_touched`/`commit_messages` for Collector-daily units, `counts`
  for Collector-weekly (manifest) units. A manifest-sourced context
  carrying no raw text is expected and correct, not an error — it
  reflects what that source actually has.
- `CanonicalUnit.metadata` gained a `source_type` key (both adapters)
  and `commit_messages`/`mode` keys (`adapt_daily_brief()` only) to
  make this possible — confirmed via TDD (RED then GREEN,
  `strategy_layer/adapters/test_collector.py`).
- `daily_linkedin_author.py` no longer reads
  `collector/data/daily_brief_<date>.json` directly —
  `default_daily_brief_path()` removed; its CLI now requires an
  explicit path to a `DailyBrief`-shaped JSON, produced by
  `author/linkedin_verdict_reader.py` from a run's `AuthoringContext`
  list. `build_prompt()` and everything downstream are unchanged — they
  only ever depended on the dict's shape, never its origin. Confirmed
  via a real end-to-end run (`strategy_layer/run_linkedin_pilot.py`)
  against current, real `daily_brief_2026-09-14.json` data: real
  Russian commit-message text reached the constructed prompt's
  `commit_messages` field.
- **Anti-"junk drawer" safeguard:** `metadata` is write-once per source
  adapter (each adapter constructs it fully at `CanonicalUnit`
  creation; nothing downstream mutates it — enforced structurally by
  `CanonicalUnit`'s own `frozen=True`). A per-`source_type` metadata-
  key whitelist test (`strategy_layer/adapters/
  test_metadata_whitelist.py`) guards against undeclared keys
  accumulating silently as sources are added later — a plain
  dict/set lookup, no new architectural layer. Planned as part of
  M6's synthetic alien-source contract test; implemented now, ahead of
  M6, since it was cheap to add immediately rather than deferred.

## Confirmation & Revisit

Validated by construction: `author/test_authoring_context.py` (5/5),
`author/test_linkedin_verdict_reader.py` (4/4),
`strategy_layer/adapters/test_metadata_whitelist.py`, plus the real
end-to-end run above. Revisit if a future source adapter's raw
material doesn't fit `AuthoringContext`'s current field set (e.g. a
source with neither counts nor commit-message-shaped text) — extend
the model then, per a new ADR extending this one's shape (Immutable
Lineage, `docs/adr/0011`), not an edit to this file.

## Source

M4 implementation session, 2026-09-15, following the owner's decision
(made before this task began) rejecting the verdict-passthrough and
external-database alternatives, and the mandatory codebase-wide search
this project's `docs/CONSTITUTION.md` requires before any diff
changing operation state.
