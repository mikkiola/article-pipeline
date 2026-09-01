---
id: ADR-0042
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0042: Cowork-Layer Practice Boundary — Practice-Only, No-File Conventions

## Status

Accepted.

## Context & Constraints

`docs/CONSTITUTION.md` is the sole recognized source of truth for
article-pipeline's governance (owner decision, already in effect;
see this file's opening line: "nothing about the product's current
state... nothing about specific decisions... nothing about the plan...
nothing about open questions" if it isn't in the appropriate canonical
document).

Separately, the owner's Cowork layer — the custom project instructions
for the "Ольга_статьи_атомы" Claude.ai project — references six working
practices by name: `obsidian-notes`, `content-social`, `human-text`,
`docops-swagger`, `ods-ecosystem`, `incident-escalation`. These are real,
actively used conventions, not aspirational or abandoned ones. A prior
audit series confirmed none of the six exist as a physical `SKILL.md` or
equivalent code artifact anywhere this repo can see: not in
`mikkiola/article-pipeline`, not in `mikkiola/tooltempest`, and not
under `~/.claude/skills/` on the owner's machine. `docops-swagger` and
`ods-ecosystem` specifically trace to a Claude.ai-internal server path
(`/mnt/skills/user/...`) that was never materialized in any real
repository — confirmed by `~/Downloads/ods-arch`'s git history
containing zero commits touching any `SKILL.md`. `incident-escalation`
has a separate origin from the other five (a distinct Cowork document
describing it as an already "created and activated" Skill governing
stop-and-ask behavior, not the automation/content checklist the other
five belong to) but shares the same defining property: no file, real
practice.

Without an explicit note, a reader relying only on this repo has no way
to learn that part of the owner's actual working process runs through a
layer this repo cannot represent — creating a silent gap between
documented process and lived process.

## Decision

Add a short, note-only section to `docs/CONSTITUTION.md` acknowledging
these six names as practices in active use whose actual source is the
Cowork layer's own `project_instructions.md`, not this repository. The
note names the six explicitly, states plainly that they are
practice-only conventions with no corresponding file anywhere this repo
can see, and cites this ADR. The note carries no registry semantics —
it does not present them as if they were tracked skills, entries in a
manifest, or dormant code.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| **A. Omit entirely — CONSTITUTION.md stays silent on the Cowork layer.** | Rejected — leaves the exact silent gap this ADR exists to close: a reader trusting this repo as the sole source of truth would have no way to know six named, actively-used practices exist outside it. |
| **B. List them as if they were real skills or registry entries.** | Rejected — fabricates the existence of artifacts that don't exist. This project has already twice found and fixed the failure mode of one component inferring another's state from unstructured or fictional structure (see ADR-0040's citation of the same class of bug); presenting a practice as a tracked skill would manufacture a new instance of it. |
| **C. Chosen — a boundary-acknowledgment note with no registry semantics.** | Names the six, states they are practice-only/no-file, points to the actual source (Cowork's `project_instructions.md`) and to this ADR for rationale — closes the gap without inventing structure that isn't there. |

## Consequences

- `docs/CONSTITUTION.md` stays honest about its own coverage boundary:
  a reader now knows part of the owner's real workflow lives outside
  the repo, and where to look for it.
- These six are explicitly excluded from any future skill-quality
  classification or testing effort (e.g. skill-conformance checks a
  later session might build) — they are not testable artifacts, and
  treating them as such would be applying code-quality tooling to
  something that isn't code.
- Does not create, reserve, or imply any obligation to eventually build
  a `SKILL.md` for any of the six. Materializing one is a separate,
  later decision, not implied by this ADR.
- Does not touch the unrelated DELETE decision covering the other
  skill/entity names identified in the same audit series — those are
  out of scope for this ADR and are not named here.

## Confirmation & Revisit

Revisit (via a new, superseding ADR — never an edit to this one, per
Immutable Lineage, ADR-0011) if any of the six practices is later
materialized as a real `SKILL.md` or equivalent artifact in this repo
or `tooltempest`. At that point this ADR's note in `docs/CONSTITUTION.md`
should be superseded, not silently dropped, since the boundary fact it
records would have changed.

**Source.** Audit series confirming physical non-existence of the
12-name Cowork skill-checklist (`~/Downloads/CoworkImport/Ольга_статьи_атомы/project_instructions.md:22`,
`~/Downloads/CONSTITUTION_ap.docx:78,159`) and `~/Downloads/ods-arch`'s
git history (zero `SKILL.md` commits); owner decision, this session, to
treat these six as practice-only/no-file rather than FREEZE/DELETE.
