# D-025 Experimental Brief — DRAFT

**Status: DRAFT**
This document is not an architectural decision and does not override
ADR-0025 or ADR-0029.

This is an experimental-design draft, not an ADR and not a decision
record. Its purpose is to preserve the current experimental-design
reasoning for the follow-up D-025 experiment between sessions, without
prematurely converting unresolved choices into normative decisions.
Anything marked OPEN below is genuinely undecided — a future session
should not treat it as settled by virtue of appearing in this file.

## 1. Causal question

Does context loss in Claim Extraction's `novelty`+`basis` output
contribute to Evidence Package's low verification rate? Originally
diagnosed in ADR-0025. ADR-0029 found the Milestone 4 experiment
confounded (query text and assessment pass varied together) and left
the question neither confirmed nor refuted. This brief is planning for
a follow-up experiment that isolates the confound per ADR-0029's
reversal condition.

## 2. Independent variable

Only query text is intended to vary between control and treatment.

- **Control query**: the original `novelty`+`basis` query (pre-
  context_layer formula).
- **Treatment query**: the same query plus the context enrichment
  introduced by `context_layer` / Milestone 3 / commit `bb549ee`
  (tags and wiki-links appended to the base query).

All other experimental conditions are intended to stay fixed — see
Section 8.

## 3. Assessment methodology

ADR-0029's reversal condition permits either of two ways to hold
assessment methodology constant while varying only the query:

a) the same evaluation pass reused across the old and new queries, or
b) a fixed scoring rubric applied identically.

The current architectural choice is **(b), a fixed scoring rubric**.
This choice is a new architectural judgment made for this experiment —
it is not a preference stated by ADR-0029 itself. ADR-0029 leaves both
options open; this brief picks one for planning purposes only, and
that pick is not yet a decision record.

## 4. Experimental design structure

Structural options for applying the chosen rubric (separate from the
Rubric Nature Question in Section 5 — these are option labels A/B, not
(i)/(ii)):

- **Structural option — current preference, not yet finally decided**:
  apply the same rubric to both the control and treatment result sets.
- Do not use the historical interactive assessment (the original
  2026-08-13 run's assessment) as the control measurement if doing so
  would create asymmetric assessment methodology between control and
  treatment — i.e., the control side must be scored the same way the
  treatment side is scored, not read off the historical run's
  recorded `status` values.
- Re-scoring the historical control under the new rubric is a **new
  experimental result**, distinct from and not a substitute for the
  historical interactive assessment recorded in
  `evidence_run_20260813T114717.json`.
- Re-scoring must never modify or overwrite the historical
  `evidence_run_20260813T114717.json` or its recorded `status` values.
  Immutable Lineage applies (see Section 6).
- A retrospective re-scoring may produce a different status from the
  historical interactive assessment for the same Claim. That
  difference is, by construction, an **assessment-methodology
  effect** (old interactive pass vs. new fixed rubric), not evidence
  of a query effect. It does not by itself speak to the causal
  question in Section 1.

## 5. Assessment rubric — Rubric Nature Question RESOLVED, rubric content still OPEN

**Rubric Nature Question** (kept distinct from the Option A/B choice
in Section 4 to avoid confusing the two): should the experimental
rubric be —

(i) an explicit operationalization of the existing Evidence Package
    `verified` criterion, without changing that criterion itself; or

(ii) a separate experimental scoring layer, distinct from the
     production `verified` criterion?

**Resolved in favor of (ii), a separate experimental scoring layer.**

**FINDING (closes the question):** a read-only audit of `SPEC.md`,
`context_layer/SPEC.md`, and `evidence_package/write_evidence.py`
found no formalized content-level rule anywhere in this project
defining what makes a source `verified` — only a four-value status
enum, with assignment happening entirely through interactive
judgment (`write_evidence.py` performs no content validation beyond
checking `status` is one of the four allowed strings). Both `SPEC.md`
and `context_layer/SPEC.md` explicitly and separately defer any
change to the `verified` criterion as future, out-of-scope work.
Therefore option (i) is not achievable as stated — there is no
existing content-level criterion to operationalize, only an enum plus
interactive practice. This finding, not a preference, is what
resolves the question in favor of (ii).

**SEPARATE CAUTION** (does not bear on the (i)/(ii) choice, applies to
whichever option had been chosen): the only concretely documented
precedent for how `verified` has been judged in practice is the
single `_04` Claim case from ADR-0029 (AdIndex.ru accepted after
full-page reading and finding topical/causal support; begemot.ai
rejected as an AI-generated source, not a human expert/researcher).
Two observed factors from one case are a thin evidentiary base for
designing a full rubric — this is a caution about the difficulty and
care needed when the rubric is actually written (a later, separate
step), not evidence relevant to the (i)/(ii) choice itself.

Production Evidence Package's `verified` criterion is **not** being
changed, redefined, or improved by this resolution. The experimental
rubric is a new, separate measurement instrument for testing the
causal hypothesis in Section 1 only — it has no effect on production
behavior.

The **content** of the rubric (the scale, criteria, pass/fail line) is
**not** written in this edit and remains a separate, future
architectural step, deliberately not combined with this resolution.
Whichever option had been chosen, the production Evidence Package
`verified` criterion must not be modified as part of this experiment
(Section 8).

## 6. Control-run re-scoring and Immutable Lineage

Any re-scoring of the historical control run (Section 4) produces a
new artifact — it does not edit, overwrite, or supersede
`evidence_run_20260813T114717.json` in place. The historical file and
its recorded `status` values remain untouched, consistent with this
project's Immutable Lineage principle (the same principle governing
`pilot_run_*.json` and `evidence_run_*.json` elsewhere in this
project). The exact form of the new artifact (naming, location,
schema) is not decided by this draft.

## 7. Outcome interpretation — OPEN

What observations would constitute "confirms," "refutes," or
"inconclusive" for the causal question in Section 1 is not decided
here. No numerical thresholds, source-count requirements, AI-source
rules, or verification criteria are proposed in this draft. This is
left as an open decision for a future session or ADR.

## 8. Fixed conditions / inherited constraints

- The Evidence Package `verified` criterion must not be modified as
  part of this experiment — inherited directly from ADR-0025's
  deferral of any fix to that criterion "until this Layer 2 issue is
  resolved."
- Search backend (`search_backend.py`), `requests_used` budget
  behavior, and the Claim set under test should remain fixed unless a
  future session explicitly decides otherwise and records why.
- Only query text (Section 2) is the intended independent variable.

## 9. Open decisions

Consolidated from Sections 4, 5, and 7 — a single entry point for the
next session to see everything unresolved without reading the whole
file:

- **Rubric content (Section 5)**: no actual rubric — scale, criteria,
  or pass/fail line — has been written yet. Section 5's caution
  applies: the only concretely documented precedent is a single
  Claim case (ADR-0029's `_04`), a thin evidentiary base for
  designing a full rubric.
- **Structural option (Section 4)**: applying the same rubric to
  both control and treatment sets is the current preference, but is
  explicitly noted as not yet finally decided.
- **Outcome interpretation (Section 7)**: what counts as "confirms,"
  "refutes," or "inconclusive" for the causal question is not decided.

## 10. Sources

- ADR-0025 — original context-loss diagnosis; source of the
  `verified`-criterion-must-not-change constraint (Section 8).
- ADR-0029 — found the Milestone 4 experiment confounded; source of
  the two assessment-methodology options in Section 3 and the
  reversal condition this brief is planning against.
- Commit `bb549ee` (context_layer Milestone 3) — introduces the
  treatment query's context-enrichment mechanism (Section 2).
- `evidence_package/output/evidence_run_20260813T114717.json` — the
  historical control run referenced in Sections 4 and 6.
- `docs/BACKLOG.md`, P0 section — tracks the open follow-up experiment
  this brief is planning for.
