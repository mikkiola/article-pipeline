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

**Resolved: a paired design on the same Claim.** Each Claim is run
through both the control query (novelty+basis) and the treatment
query (novelty+basis+context) under identical search procedure and
identical search budget. The comparison is the within-Claim
difference (Δ) between the two resulting evidence sets, not a
between-group comparison across two separately-run sets of Claims.

This resolves the earlier open question about using the historical
run as control: the historical interactively-assessed run
(`evidence_run_20260813T114717.json`) is **not** used as control.
Instead, a **new** control run is produced in the same experimental
session, under the same conditions, as the treatment run. This
removes a specific risk: if the historical run and a new treatment run
were compared instead, any difference between them could reflect
changes in the search backend, ranking, page availability, code,
environment, or evaluator over the intervening time, not just the
query. This is the specific mechanism removed by the paired design —
not a general claim that all such concerns are eliminated.

Both the control and treatment evidence sets, for a given Claim, are
scored using the same frozen measurement instrument. "Frozen" here is
a **structural** requirement only — it means the instrument does not
change between scoring the control and treatment sides of a pair. It
does **not** mean the instrument's content (the scale, criteria, or
pass/fail line) has been decided; that remains open per Section 5,
unchanged by this resolution.

What remains genuinely **OPEN** and is **not** resolved by this
structural decision:

- the content of the experimental score/rubric (Section 5);
- **Blind assessment / randomized order**: RESOLVED — not used. The
  evaluator (Claude Code) knows which result set is control and which
  is treatment while scoring. Instead of blinding, post-hoc analytics
  will be collected after the experiment to check whether scores show
  a systematic bias pattern favoring treatment beyond what the Δ
  values themselves would suggest — this is a lighter-weight
  safeguard than blinding, chosen for this pilot's small scale.
- **Pairwise comparison as an additional measurement**: RESOLVED —
  not used. The 3-level score (Section 5) alone is sufficient; no
  additional "which is better" comparison is collected.
- how calibration of the measurement instrument would be done without
  leaking information from the specific control/treatment data being
  compared.

This paired design fixes the experimental **unit** (one Claim,
compared to itself under two query conditions) and removes the earlier
asymmetry concern, but does **not** by itself define what the score
measures or how strong the causal claim is — those remain separate,
later decisions.

## 5. Assessment rubric — Rubric Nature Question RESOLVED, rubric content RESOLVED

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

**Rubric content:**

A 3-level score, applied identically to each Claim's control and
treatment evidence:

- **Strong support (2)**: the source is a human expert/researcher on
  the topic (not an AI-generated source), contains direct topical/
  causal support for the Claim, confirmed by reading the full source
  page (not just the snippet).
- **Weak/partial support (1)**: the source is topically relevant but
  either (a) is AI-generated or has unverifiable authorship, or (b)
  only provides indirect/analogical connection to the Claim, not
  direct support.
- **No support (0)**: no source found, or a source was found but is
  not topically relevant to the Claim at all.

Δ (Section 7) = Treatment score − Control score, computed per Claim
using this scale.

Explicitly note: this rubric is a fixed rule for this pilot only, not
a self-learning or reinforcement-learning system. The sample size (5
Claims) is intentionally too small to support learning a general rule
— any move toward an adaptive/learned criterion is separate, future,
out-of-scope work for this experiment.

Explicitly note: this rubric is informed by the single documented
`_04` precedent (Section 5's existing caution about thin evidentiary
base still applies — this is a reasonable starting rule, not a
validated general theory of what makes sources credible).

## 6. Control-run re-scoring and Immutable Lineage

Any re-scoring of the historical control run (Section 4) produces a
new artifact — it does not edit, overwrite, or supersede
`evidence_run_20260813T114717.json` in place. The historical file and
its recorded `status` values remain untouched, consistent with this
project's Immutable Lineage principle (the same principle governing
`pilot_run_*.json` and `evidence_run_*.json` elsewhere in this
project). The exact form of the new artifact (naming, location,
schema) is not decided by this draft.

## 7. Outcome interpretation — structure resolved, significance threshold RESOLVED

**Core principle:** interpretation is based on the paired difference
(Δ = Treatment score − Control score) for each Claim, averaged across
all Claims in the experiment — **not** on a simple count or majority
of how many Claims improved. Concrete illustration of why: two
outcomes can both show "3 of 5 Claims improved" while having very
different total magnitude (e.g., small +1 improvements in 3 Claims vs.
one large +4 improvement in 3 Claims) — a majority-count rule alone
would treat these as equivalent when they are not. The mean Δ captures
magnitude; a count of improved Claims does not.

Three interpretive outcomes replace the plain confirms/refutes/
inconclusive language from Section 1 with an operational structure:

- **Positive signal**: mean Δ is positive and the improvement is
  substantively meaningful (not just barely above zero) — the exact
  numeric threshold for "meaningful" is **not** decided in this draft
  (see the open item below). No requirement that every single Claim
  individually improves.
- **No clear signal**: mean Δ is close to zero, or the pattern across
  Claims is mixed with no consistent direction.
- **Negative signal**: mean Δ is negative, or a consistent, repeated
  failure pattern is observed across multiple Claims (not just a
  single outlier).

A single Claim showing a worse treatment score than control does
**not** by itself count as a failure of the hypothesis, unless "zero
regressions allowed" is explicitly declared as a required safety
condition in advance — which this draft does **not** declare. Any
individual regression must still be recorded and looked at separately
(is it random retrieval noise, or a systematic failure mode affecting
a specific type of Claim?) rather than averaged away and ignored.

On "No clear signal" / an ambiguous result: this does **not**
automatically mean "refuted," and it does **not** automatically
trigger a bigger follow-up experiment. The first step is to examine
why the result was ambiguous (was a negative Claim random noise or a
systematic pattern? are the improvements actually attributable to the
context enrichment? are the Δ magnitudes practically meaningful or
within noise range of the scoring instrument? does one single Claim
dominate the average?). Only after that examination, if uncertainty
remains, would a larger-sample follow-up be considered — this is not
decided in advance as the automatic next step.

**Resolved**: given the 3-level scale in Section 5 (0/1/2), a mean Δ
of **at least 1.0** across the Claim set counts as a "Positive
signal" (substantively meaningful). A mean Δ between 0 and 1.0 (not
reaching 1.0) falls under "No clear signal." This threshold reflects
the coarseness of the 3-level scale — a mean shift of a full point is
a real, visible change on this scale, not sub-scale noise. This
threshold is specific to this pilot's 3-level scale and is not
intended to generalize to any future, finer-grained rubric.

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

Only one open item remains — the rest have been resolved in this and
prior commits:

- **Calibration approach (Section 4)**: how the measurement instrument
  would be calibrated without leaking information from the specific
  control/treatment data being compared is not decided.

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
