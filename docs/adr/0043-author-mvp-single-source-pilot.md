---
id: ADR-0043
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0043: Author MVP — Source Adapter / Story Builder / Channel Profile / Channel Author, Single-Source Pilot via Collector

## Status

Accepted.

## Context & Constraints

Author was entirely unimplemented before this session — `author/` held
only a `.gitkeep` placeholder, and `docs/adr/0007-strategy-layer-
separate-from-platform-adapter.md` states plainly: "None of the three
components has been implemented — all exist only as specification."
The one candidate input schema for Author (Strategy Layer's verdict
output, defined in `SPEC.md`) was itself flagged thin during the
Strategy Layer `/spec` interview: "1 WARNING (Author's input contract
only thinly defined by ADR-0007)" — never resolved.

Building Author against that schema now would mean building against
an interface nobody has validated, fed by a component (Strategy Layer)
that also doesn't exist yet. Separately, Collector (O1) — a new,
independent sibling repo — already produces a real, structured weekly
artifact: `manifest_<date>.json`, classifying real workspace file
changes three ways (`value` / `explicit_service` / `default_service`)
with per-file evidence for the `value` bucket.

Rather than wait for Strategy Layer / Multi-Source Claim Layer to
mature, or build Author against an unvalidated schema, the owner chose
to pilot Author against Collector's manifest — a single, already-real
data source — to test the thing this whole chain ultimately exists to
produce: two genuinely different, audience-appropriate article drafts
from one consistent underlying story. This architecture (four
sequential stages, one canonical story feeding multiple renderers) was
synthesized from a cross-check across multiple independent AI reviews
before being adopted, the same practice already used for Collector's
own classifier rule resolutions.

## Decision

A four-stage pipeline, not to be collapsed:

```
Collector manifest (raw)
    -> Source Adapter   (facts + evidence only, NO interpretation)
    -> Story Builder     (the ONLY stage allowed to interpret;
                           produces one CanonicalStory)
    -> Channel Profile   (two explicit profile objects — habr_ru,
                           linkedin_en — not a scalar tone parameter)
    -> Channel Author    (renders one Markdown draft per profile,
                           from the SAME CanonicalStory)
```

Both channel drafts are generated from one shared `CanonicalStory`
object — never two independent per-channel generations starting from
raw facts. `CanonicalStory` carries five fields (`core_problem`,
`change`, `insight`, `forward_lesson`, `outcome`), each required to
trace to `CanonicalEvent.facts`/`evidence`/`context`, with an explicit
placeholder string standing in wherever the input genuinely doesn't
support a claim — never a fabricated specific.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| **A. Tone-slider-only approach** — a single scalar tone parameter driving one generation function per channel. | Rejected — collapses genuinely different axes of variation (audience, purpose, evidence density, narrative structure) into one number; cannot express "high evidence density, technical problem→solution→architecture→outcome structure" versus "medium density, personal context→insight→outcome→lesson structure" as a single scalar without losing the distinction entirely. |
| **B. Independent per-channel generation directly from raw facts** — two separate generation calls, no shared intermediate story. | Rejected — the cross-check's consensus finding: two independent generations from the same raw facts risk telling two different, potentially inconsistent stories about the same event, with no single source of truth for "what actually happened" to check either draft against. |
| **C. Chosen — four-stage pipeline, one canonical story feeding multiple channel-specific renderers.** | Closes both gaps: `ChannelProfile` objects capture the real axes of variation explicitly and legibly; one shared `CanonicalStory` guarantees narrative consistency across every channel derived from it, by construction rather than by discipline. |

## Consequences

- A future Strategy-Layer-fed Author path is not precluded by this
  decision. It would need its own adapter producing a
  `CanonicalEvent`/`CanonicalStory` pair (or an equivalent shape) from
  Strategy Layer's verdict schema — `story_builder.py`,
  `channel_profiles.py`, and `channel_author.py` are already
  source-agnostic and would not need rewriting, only a second Source
  Adapter alongside `source_adapter.py`.
- Author's current dependency, per `docs/ARCHITECTURE.md`, is
  Collector's manifest, not Strategy Layer — a deliberate, temporary
  rerouting while Phase 3's claim-source path stays paused (see
  `docs/ROADMAP.md`'s Current pointer and `docs/BACKLOG.md`'s
  `[B-056]` for the full pause record and resume condition).
- A real gap this pilot surfaced in Collector — its own repository had
  no rule that could ever classify its own files as `value` — was
  fixed upstream, in Collector's own classifier, not worked around in
  Author. Author's facts and evidence stay honestly sourced from
  whatever Collector actually reports, rather than compensating for a
  source-side gap on the consuming end.
- Known limitations carried forward from the pilot, not resolved here:
  no runtime translation to Russian (Habr's body prose is the same
  English canonical `CanonicalStory` text, not machine-translated —
  this is a first, inspectable, hand-editable prototype by explicit
  design, not the final automated-without-review target state); a
  manifest snapshot older than the event it describes will produce a
  thin, honestly-placeholdered story rather than a rich but fabricated
  one, by design.

## Confirmation & Revisit

Validated by construction: `author/test_pipeline.py`'s 5 tests pass,
including a regression check (added after an earlier iteration of this
same architecture was found to render two sections with identical body
text, from a stage-to-field mapping bug — fixed before this ADR was
written) that no two sections within one channel's draft repeat the
same `CanonicalStory` field. Two real Markdown drafts were generated
from Collector's real, current manifest data — not synthetic fixtures.

Revisit when Strategy Layer or the Multi-Source Claim Layer expansion
resumes (see `docs/BACKLOG.md`'s `[B-056]`) and needs its own path into
Author — via a new ADR extending this one's shape, per Immutable
Lineage (`docs/adr/0011`), not an edit to this file.

**Source.** Owner decision, this session, following a cross-check
across multiple independent AI reviews of the four-stage architecture;
built and validated against Collector (O1)'s real manifest data.
