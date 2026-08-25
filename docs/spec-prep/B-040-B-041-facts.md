---
type: spec-prep-facts
relates_to: [B-040, B-041]
created_at: 2026-08-24
source_type: mixed
---

# Fact inventory for [B-040] / [B-041] — pre-`/spec` prep

Read-only fact-gathering only. No design decisions are made or
proposed in this document; open forks are recorded neutrally for a
future `/spec` interview to resolve.

## Part 1 — [B-040] Internal Facts

*source_type: verbatim — today's direct reads against this repo.*

**`docs/ARCHITECTURE.md`** — 38 lines total. Breakdown:
- Line 1: H1 title.
- Lines 3–7: prose paragraph (5 lines) — the only prose in the file,
  which states its own "Every fact is a table cell — no prose
  sections" principle.
- Lines 9–23: Table 1 (header + separator + 14 data rows = 16 lines).
- Line 25: `## Repositories` heading.
- Lines 27–31: Table 2 (header + separator + 3 data rows = 5 lines).
- Line 33: `## Models used by this project` heading.
- Lines 35–38: Table 3 (header + separator + 2 data rows = 4 lines).
- Total table-row lines (`grep -c "^|"`): 24.

**`docs/ROADMAP.md`** — 43 lines total. Breakdown:
- Lines 3–6: preamble prose (4 lines).
- Lines 10–18: one table (header + separator + 7 data rows = 9 lines).
- Lines 22–28: "Current pointer" prose (7 lines).
- Lines 32–39: "Dependency chain" — fenced ASCII arrow-diagram (8
  lines including fences).
- Line 43: "Open decisions" — one-line pointer sentence.
- No stated "table-only"/"no prose" principle anywhere in this file
  (unlike `docs/ARCHITECTURE.md`).

**"Current pointer" section, sentence-by-sentence (exact quotes):**
1. *"Phase 2.5's causal question is resolved, partially confirmed —
   the P0 item that tracked it is done and removed from
   `docs/BACKLOG.md`'s P0 section, which is now empty."* — state fact.
2. *"Phase 3 is no longer blocked on this question."* — state/
   consequence fact.
3. *"The atom-tag-disambiguation P1 item (found via the same
   experiment) is a targeted, non-blocking follow-up — see
   `docs/BACKLOG.md`."* — state fact plus provenance.
4. *"Next work can pull from P1 items or begin Phase 3 planning."* —
   **advisory/recommending a next action, not reporting current
   state** — structurally different from sentences 1–3, and the
   hardest of the four to losslessly tabulate as a fact.

**Existing stated principle:** `docs/ARCHITECTURE.md` line 3: *"Every
fact is a table cell — no prose sections."* No equivalent statement
exists in `docs/ROADMAP.md`.

## Part 2 — [B-040] External Research

*source_type: inferred — owner-provided synthesis of 3 independent AI
models' architect-chat research pass, 2026-08-24. The full original
research text was requested and not successfully transmitted through
this channel after three attempts; what follows is a synthesis of the
specific claims, citations, and conclusion-split the owner directly
asserted, not a verbatim quotation of the original passes.*

**Cited sources (URLs as given):**
- Open Knowledge Format (OKF) v0.1: `cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/`
- OKF v0.2: `cloud.google.com/blog/products/data-analytics/okf-v0-2-adds-trust-signals/`
- Karpathy's LLM Wiki gist: `gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
- MADR/ADR documentation-format practice (general reference, no
  specific URL given).

**Unanimous conclusion (all 3 passes):** reject "remove ALL prose" as
the design for table-only conversion.

**One point of disagreement:** 2 of 3 passes recommend keeping the
"Current pointer" section's advisory sentence (quoted above, sentence
4) as prose rather than forcing it into a table row; 1 of 3
recommends removing/converting it, treating it as derivable from the
table's own state facts rather than needing separate prose.

## Part 3 — [B-041] Internal Facts

*source_type: verbatim — today's direct reads against this repo.*

**`docs/CONSTITUTION.md` lines 302–308 (exact quote):**
> `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and this file describe
> decisions in prose without citing a specific ADR number. If a future
> edit reintroduces a number citation in any of these three, that's a
> rule violation to fix in that file, not a reason to loosen this
> rule. A destination-invariant check (`scripts/check-adr-citation.sh`,
> wired into `scripts/hooks/pre-push`) enforces this mechanically
> against all three files — not just a prose expectation.

This is the one existing CONSTITUTION.md rule confirmed both stated in
prose and mechanically enforced via an automatic hook.

**`scripts/verify.py`'s 7 functions (name — what it checks):**
- `find_spec_files()` — locates SPEC.md at repo root + one level into
  component subdirectories.
- `resolve_component_name()` — maps a SPEC.md to the component
  directory it documents.
- `isolate_milestones_section()` — extracts text between `##
  Milestones` and the next `##` heading.
- `classify()` — determines whether a SPEC.md has a valid
  inline-checkbox Milestones section.
- `validate_inline_spec_structure()` — checks every checkbox line has
  non-empty description text.
- `parse_milestone_fields()` — extracts optional `verify:`/`done-when:`
  metadata, whole-document scan ([B-036]).
- `check_milestones_boundary_integrity()` — cross-checks isolated vs.
  whole-document checkbox counts to detect boundary truncation
  ([B-039]).

**`scripts/check-adr-citation.sh`:** fails if a literal `ADR-[0-9]+`
citation is found in `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, or
`docs/CONSTITUTION.md` (`docs/BACKLOG.md` explicitly exempted).

**`scripts/check_adr_numbering.py`'s 3 checks:** (a) filename matches
`NNNN-slug.md`, (b) filename number matches the file's own header-line
number, (c) no ADR number reused across multiple files.

**10-row rule-coverage table (from prior fact-gathering pass, same
session):**

| Rule (paraphrase) | Script coverage |
|---|---|
| Product-scope meta-rule (line 8) | None — not a document-content rule |
| README/ARCHITECTURE/etc. staleness update (lines 71–76) | Coarse proxy only: `scripts/check-doc-pairing.sh` warns on missing pairing, doesn't check content staleness |
| Autonomous ADR creation "when basis is sufficient" (lines 79–86) | None |
| ADR Immutable Lineage — never edited after acceptance (lines 95–97) | None found anywhere in `scripts/` |
| TDD "required whenever risk profile justifies it" (lines 143–146) | None (judgment-based) |
| Sensitive-ops execution-environment rule (lines 170–177) | None |
| "Verify no existing component covers responsibility" (lines 178–185) | None |
| Codebase-wide search before certain diffs (lines 186–190) | None |
| ToolTempest `MANIFEST.txt` completeness-check obligation (lines 204–210) | Names a real script (`scripts/check_manifest.py`) but it is **not wired into any hook** — zero references in `scripts/hooks/pre-commit`, `pre-push`, `doc_sync.py`, `install-hooks.sh` |
| Task-scoping format requirement (lines 336–341) | None (meta-rule about task framing) |
| **ADR-citation rule (lines 302–308)** | **Mechanically enforced** via `scripts/check-adr-citation.sh`, wired into `scripts/hooks/pre-push` |

Summary: 1 of 10 rules mechanically enforced automatically; 1 names a
real script that exists but isn't wired in; 8 have zero corresponding
script anywhere in `scripts/`.

## Part 4 — [B-041] External Research

*source_type: inferred — owner-provided synthesis of 3 independent AI
models' architect-chat research pass, 2026-08-24. Same transmission
caveat as Part 2: synthesis of the owner's directly-asserted claims,
not verbatim quotation.*

**Convergent theme cited:** "Fitness Functions" (evolutionary-
architecture terminology) / "policy-as-code" / a "baseline-and-ratchet"
enforcement pattern — a rule is checked mechanically against a
recorded baseline, and the baseline only ever tightens (ratchets),
rather than requiring either full immediate enforcement or none.

**Named tools cited as real-world examples of this pattern:** ESLint
(baseline tooling), Betterer, NVIDIA TensorRT-LLM's own
`CODING_GUIDELINES.md`, SwiftLint, alint.

**Convergent recommendation:** a tiered-enforcement model — not "every
rule mechanically enforced or none" — a graded classification by
enforceability rather than a single binary rule.

**One dissenting position:** Pass 1's stricter recommendation —
"delete unenforceable rules" (if a CONSTITUTION.md rule cannot be
mechanically checked, remove it rather than leave it as an unenforced
prose expectation) — differing from the other two passes' more
permissive tiered-model consensus.

## Pre-spec skill output

`~/.claude/skills/pre-spec/SKILL.md` read in full and applied
literally, as a pure router (it performs no diagnosis itself — it
checks for explicit signals and, when present, invokes
`finding-unknowns`/`phrase-decomposer` directly).

**Signal check:**
- [B-040]: `finding-unknowns` signal present (decision depends on an
  architecture choice not yet made). No clear `phrase-decomposer`
  signal.
- [B-041]: both signal types present — `finding-unknowns` (architecture
  choice re: scope/enforceability) and `phrase-decomposer` (the term
  "format/structural requirement" admits 2+ plausible readings).

Per pre-spec's routing rule ("both signal types fired → invoke both
sensors independently, not sequentially"), both sensors were actually
invoked (not simulated) for [B-041]; `finding-unknowns` alone for
[B-040].

**`finding-unknowns` output — [B-040]** (2 WARNING, 0 BLOCKING):
```
Finding
├── type: knowledge
├── severity: warning
├── subject: Whether the ASCII dependency-chain diagram counts as
│   "prose" under table-only format, or is exempt as a diagram
├── evidence: Diagram confirmed to exist (8 lines, lines 32-39); no
│   existing rule/precedent in this repo addresses ASCII-diagram
│   handling under a table-only principle
├── resolution: unresolved — open architecture choice, left for
│   /spec's own decision, not blocking
└── status: open

Finding
├── type: knowledge
├── severity: warning
├── subject: Whether the "Current pointer" section's advisory sentence
│   can losslessly tabulate, or is structurally exempt like
│   ARCHITECTURE.md's Validation-column narrative
├── evidence: Confirmed via direct quote-by-quote read that this
│   sentence is advisory, unlike its 3 sibling sentences; SPEC.md's
│   own M6 section already precedent for excluding narrative/judgment
│   content from a related mechanically-diffable-facts rule
├── resolution: unresolved — open architecture choice, left for
│   /spec's own decision, not blocking
└── status: open
```

**`finding-unknowns` output — [B-041]** (3 WARNING, 0 BLOCKING):
```
Finding
├── type: knowledge
├── severity: warning
├── subject: Whether the new principle applies retroactively to all 8
│   currently-uncovered rules or only prospectively to new rules
├── evidence: Confirmed today's inventory: 8/10 rules uncovered; scope
│   not stated in [B-041]'s own text either way
├── resolution: unresolved — open architecture choice, left for
│   /spec's own decision, not blocking
└── status: open

Finding
├── type: knowledge
├── severity: warning
├── subject: Whether inherently judgment-based rules (TDD threshold,
│   "verify no existing coverage", search-before-diff) are candidates
│   for mechanical enforcement at all, or structurally exempt
├── evidence: Confirmed these rules have no corresponding script and
│   appear judgment-based on inspection (execution-context/behavioral
│   rules, not document-content rules)
├── resolution: unresolved — open architecture choice, left for
│   /spec's own decision, not blocking
└── status: open

Finding
├── type: knowledge
├── severity: warning
├── subject: Whether check_manifest.py's named-but-unwired status
│   counts as a relevant partial-compliance precedent, or is out of
│   scope (ToolTempest-owned)
├── evidence: Confirmed: script exists, zero hook references found in
│   scripts/hooks/, doc_sync.py, install-hooks.sh
├── resolution: unresolved — open architecture choice, left for
│   /spec's own decision, not blocking
└── status: open
```

**`phrase-decomposer` output — [B-041]** (1 BLOCKING):
```
Finding
├── type: semantic
├── severity: blocking
├── subject: "format/structural requirement" — scope of what counts
│   as a "format rule" this principle governs
├── evidence: Semantic variance sensor — term admits narrow (document-
│   content conventions only) vs. broad (any prescriptive
│   CONSTITUTION.md statement) readings; today's inventory (8/10 rules
│   uncovered, several judgment-based/behavioral) makes the
│   distinction consequential, not academic
├── resolution: BLOCKING — narrow reading bounds /spec to extending an
│   existing pattern; broad reading requires /spec to design a tiered
│   enforcement taxonomy for a heterogeneous rule set. Owner decision
│   needed on which scope [B-041] actually means before /spec can
│   proceed.
└── status: open
```

**Pre-spec merge result:**
- **[B-040]:** no BLOCKING from either sensor → "Проверено, блокеров
  нет. Можно в /spec." (2 WARNING findings pass through as `/spec`
  context.)
- **[B-041]:** 1 BLOCKING (from `phrase-decomposer`) → per pre-spec's
  merge rule, this had to be closed before a `/spec` interview on
  [B-041] could proceed. **Resolved 2026-08-25 — see "Open decisions"
  below.** [B-041] is now clear for `/spec`.

## Open decisions

Recorded neutrally — no proposed answers.

**[B-040]:**
1. Does the ASCII dependency-chain diagram count as "prose" to
   convert, or is it exempt?
2. Does the "Current pointer" section's advisory sentence ("Next work
   can pull from P1 items or begin Phase 3 planning.") get tabulated,
   kept as prose, or removed as derivable? (External research split:
   2 of 3 passes keep it as prose; 1 of 3 recommends removing it.)

**[B-041]:**
1. **RESOLVED, 2026-08-25.** Was blocking, per `phrase-decomposer`:
   does "format/structural requirement" mean narrowly (document-content
   conventions, the same category as the existing ADR-citation
   precedent) or broadly (any prescriptive CONSTITUTION.md statement,
   including behavioral/process rules)? **Owner's decision: narrow.**
   In the owner's own words: *"у нас есть правило токенов и затрат,
   логично что проверяем только то что легко проверяется...
   автоматизация автоматизирует только то что можно автоматизировать"*
   — enforcement covers only what a script can cheaply and mechanically
   verify (document format: headings, IDs, citation patterns, field
   presence), per this project's existing token/cost-consciousness
   principle. Not a judgment that behavioral/process rules are
   unimportant — a judgment that they cannot be verified by a script
   in principle, and attempting to would waste effort on an
   unachievable goal. This unblocks `/spec` for [B-041], per pre-spec's
   own merge rule — does not itself write the new CONSTITUTION.md
   principle's text, which remains `/spec`'s job.
2. **RESOLVED, 2026-08-25 — same decision as (1).** Was: if broad, how
   should the 4+ judgment-based, currently-unenforceable rules found in
   today's inventory (TDD threshold, "verify no existing coverage,"
   search-before-diff, sensitive-ops environment) be classified? Now
   moot — the narrow-scope decision above means these rules are
   explicitly **not candidates for mechanical enforcement at all**, not
   merely unresolved. (External research's two contrasting answers — a
   convergent tiered-enforcement model from 2 of 3 passes, vs. Pass 1's
   dissenting "delete unenforceable rules" position — are both
   answers to the broad-reading branch this decision didn't take;
   recorded above for reference, not applicable to the narrow reading
   chosen.)
3. Does `check_manifest.py`'s named-but-unwired status matter to this
   decision, or is it out of scope as a ToolTempest-owned script?
   **Still open** — not resolved by the scope decision above.
