---
id: ADR-0040
status: Accepted
supersedes: ADR-0036
superseded_by: null
source_type: inferred
---

# ADR-0040: ADR Status/Supersession Fields Move to Frontmatter

## Status

Accepted

## Context & Constraints

ADR-0036 (Accepted, 2026-08-20) established the ADR lifecycle contract:
a `Proposed` → `Accepted` → `Deprecated`/`Superseded` state machine, an
explicit `Supersedes`/`Superseded by` field pair, and a generated
`ADR-INDEX.md` — but specified all three as body-level prose fields (a
`Status` section, a `Supersedes: ADR-NNNN` line in the new ADR's own
field set, and a `Superseded by ADR-MMMM` update to the old ADR's
`Status` line).

The Metadata/ID Layer `/spec` interview (2026-08-22) designed a
machine-parseable frontmatter layer for `docs/BACKLOG.md`/
`docs/ROADMAP.md`/ADRs, intended eventually to feed ODS-KG's Document
Fact export. For ADRs this meant adding YAML frontmatter fields
including `status`, `supersedes`, `superseded_by` — implemented across
all 39 existing ADRs in this same session's Step 4.

This directly relocates what ADR-0036 already decided at the body
level. Per `docs/CONSTITUTION.md`'s ADR discipline ("never edited after
acceptance — a changed decision becomes a new ADR that supersedes the
old one"), moving these fields' canonical home from prose to
frontmatter is itself a decision requiring a new ADR, not a silent edit
to ADR-0036 — even though ADR-0036 was also migrated to the new 6-block
body format as one of the 39 in Step 4.

**Explicit scope constraint, per the owner:** this ADR does not touch
ADR-0036's actual lifecycle logic or its 4-value `Status` enum
(`Proposed`/`Accepted`/`Deprecated`/`Superseded`) — those carry forward
unchanged. Scope is field-placement only.

## Decision

The `Status` value (one of ADR-0036's four enum values) and the
`Supersedes`/`Superseded by` relationship now live in each ADR file's
YAML frontmatter (`status`, `supersedes`, `superseded_by` keys) as the
canonical, machine-readable home for these three facts — replacing
ADR-0036's original body-level design (a `Status` line/section plus a
`Supersedes: ADR-NNNN` line in prose).

The body's own `## Status` section is retained for freeform
human-readable elaboration (implementation notes, caveats, known
issues) — e.g. ADR-0032's body `## Status` section still reads
"Accepted — implemented and regression-tested (2026-08-19), commit
404c24c..." — but the frontmatter `status` field, not this prose, is
what a script reads to determine an ADR's lifecycle state or
supersession relationships.

## Alternatives & Rationale

Two alternatives were available, per the owner's own framing during the
interview:

**A. Leave ADR-0036's body-level field design in place** — frontmatter
carries only `id` and `source_type`, not `status`/`supersedes`/
`superseded_by`. Rejected: this would leave the `ADR-INDEX.md`
generator (Step 6) parsing two different possible sources of truth
depending on which fields it reads — body prose for some facts,
frontmatter for others — with no clear reason for the split. A script
reading `## Status` prose to extract a 4-value enum is also exactly the
kind of "one component infers another's state from unstructured text"
failure class this project has already found and fixed twice before
(see `docs/BACKLOG.md`'s closed "Audit implicit text-based contracts in
the DocOps protocol" entry). A structured frontmatter field is strictly
more robust for exactly the purpose ADR-0036 itself wanted
(`Supersedes`/`Superseded by` as "an explicit, checkable field rather
than relying on prose recognition").

**B. Chosen — frontmatter becomes the canonical home for
`status`/`supersedes`/`superseded_by`, via a new superseding ADR.**
Chosen specifically because it doesn't touch ADR-0036's actual decision
(the state machine, the four enum values, the concept of a
Supersedes/Superseded-by relationship, the generated index) — only
where those facts are written down. This is a narrow, mechanical
relocation, not a re-litigation of ADR-0036's substance.

## Consequences

- Step 6's `ADR-INDEX.md` generator reads `status`/`supersedes`/
  `superseded_by` from frontmatter across all 40 ADR files, not by
  parsing body prose — one consistent source of truth.
- ADR-0036's own `Status` is updated, this same session, to
  `Superseded by ADR-0040` (frontmatter `superseded_by` field and body
  Status section), per normal ADR discipline. ADR-0036 was already
  migrated to the new 6-block body format in Step 4 (it's one of the
  39); this ADR's supersession layers on top of that already-migrated
  file, not in conflict with it.
- Every ADR from this one forward (and all 39 migrated in Step 4)
  carries `status`/`supersedes`/`superseded_by` in frontmatter as the
  canonical fields — a future script or person needing an ADR's
  lifecycle state or supersession relationship should read frontmatter,
  not grep body prose for "Status:" or "Supersedes:".
- Does not change ADR-0036's `Proposed`→`Accepted`→`Deprecated`/
  `Superseded` state machine, its four enum values, or its
  point-level-supersession-is-unsupported finding — ADR-0035's
  relationship to ADR-0033 remains unrepresented in both the old and
  new field homes alike, exactly as ADR-0036 already flagged.

## Confirmation & Revisit

Validated by construction: Step 4's migration of all 39 existing ADRs
(including ADR-0036 itself) already populated `status`/`supersedes`/
`superseded_by` in frontmatter, and Step 6's `ADR-INDEX.md` generator
(built immediately after this ADR, same session) reads exclusively from
those frontmatter fields — a correct, complete generated index with no
body-prose parsing is this ADR's own decision working as intended.

Revisit if a future need arises for a fact this frontmatter shape can't
represent — e.g. ADR-0035/ADR-0033's point-level supersession case,
which ADR-0036 already flagged as unmodeled and this ADR does not
resolve either — via a new, superseding ADR, not an edit to this one or
to ADR-0036.

**Source.** Metadata/ID Layer `/spec` interview, 2026-08-22
(Confirmation 2's two open forks, resolved by the owner: adopt
ADR-0036's enum unchanged; frontmatter replaces ADR-0036's body-level
Supersedes/Superseded-by design, via a new narrowly-scoped superseding
ADR). Implementation session, same date, Step 5.
