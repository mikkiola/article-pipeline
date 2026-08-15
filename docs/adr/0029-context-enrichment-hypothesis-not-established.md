# 0029 — D-025's context-enrichment hypothesis: not established by the Milestone 4 experiment (confound found)

## Status
ACTIVE (diagnosis). Corrects the causal framing in commit `2b7c8a6`
(context_layer Milestone 4). Milestone 4's commit itself is not edited
or amended — Immutable Lineage; this record is where the correction
lives.

## Decision
The Milestone 4 experiment does not establish that context_layer's
query enrichment caused Claim `20260811T165911_04`'s status to change
from `unverifiable` to `verified`. A direct audit of the original
2026-08-13 run's raw search results found the responsible source
already present in that run, before context_layer existed. D-025's
original context-loss hypothesis remains neither confirmed nor refuted.

## Options
A — accept Milestone 4's commit message as written: context-enriched
query caused the one status change, treat D-025 as partially validated.
B — audit the raw result sets from both runs before accepting any
causal claim, and record the finding precisely, including if it
contradicts the commit message (chosen). C — discard the Milestone 4
experiment entirely as inconclusive and re-run before recording
anything.

## Chosen
B.

## Why

**What was observed**: 1 of 5 re-run Claims (`20260811T165911_04`)
changed from `unverifiable` (2026-08-13 original run, evidence_run
`20260813T114717`) to `verified` (2026-08-15 context_layer re-run,
evidence_run `20260815T150904`). The other 4 remained `unverifiable` in
both runs.

**What the audit found**: the source responsible for the status change
(AdIndex.ru, "Как акт наблюдения меняет поведение и валидность данных")
was present in **both** runs' raw Linkup result sets — position 6 of 20
in the original 2026-08-13 run (recovered from
`evidence_package/output/_m4_staging_20260813T114717.json`, a staging
file that captured the full result list the original interactive
assessment actually saw) and position 9 of 20 in the 2026-08-15
context-enriched re-run. The query's additive context terms did not
cause this source to appear — it was discoverable under the original
`novelty`+`basis`-only query the whole time.

**What actually changed the status**: the 2026-08-13 run's interactive
assessment evaluated a different, weaker candidate present in the same
result set (`begemot.ai`, an AI-generated content site, rejected in
that run's note as "статья AI-персоны... не верифицируемый человеческий
эксперт/исследователь") and landed on `unverifiable` without evaluating
AdIndex.ru on its merits at all. The 2026-08-15 re-run's fresh
assessment pass evaluated AdIndex.ru directly, read the full source
page (not the snippet), and found genuine topical/causal support — a
**reassessment effect**, not a **context-enrichment effect**.

**Confound identified**: Milestone 4's experiment design changed two
things at once between the old and new runs — the search query text
(context_layer's addition) and the assessment pass itself (a fresh
interactive read, by construction, since it was a new run session). It
cannot isolate which one, if either, caused the status change for Claim
`_04` from the query change alone. The staging-file audit now shows
definitively that for this specific Claim, the query change was **not**
the cause.

**Secondary, narrower, positive finding**: context_layer's additive
query change did not *destroy* the pre-existing source's
discoverability. The appended context terms shifted the rest of the
2026-08-15 result set toward an election-observation-heavy cluster
(visibly different from the 2026-08-13 result set beyond AdIndex.ru
itself), yet AdIndex.ru survived that shift and remained in the top 20.
This is a much narrower, more defensible claim than "context enrichment
fixed verification" and is recorded here as its own finding, not folded
into the main one.

**Relation to D-025**: D-025 stated the diagnosis in these exact terms —
"a line-by-line comparison of full atom text against `novelty.value +
basis.value` across all 5 pilot Claims showed a systematic pattern...
loss of domain/tag context (which exists only in the graph's tags and
wiki-links, and the extraction schema does not carry it forward)" — and
explicitly deferred any fix to Evidence Package's `verified` criterion
"until this Layer 2 issue is resolved." context_layer's Milestones 1–3
were built to address that diagnosis by carrying tags/wiki-links forward
into the search query. Milestone 4 was the first live test of whether
that fix changes Evidence Package outcomes. This ADR's finding is that
the test, as run, cannot answer that question for the one Claim where
anything changed — it does not confirm D-025's hypothesis, and it does
not refute it either.

## Constraints
No claim that context_layer's enrichment caused Claim `_04`'s status
change should be repeated elsewhere in this project (ARCHITECTURE.md,
ROADMAP.md, future ADRs) until a properly isolated experiment is run
per the reversal condition below.

## Rejected
A — rejected because it repeats a causal claim the raw data directly
contradicts; recording it as accepted history would misrepresent the
experiment's actual evidentiary weight to any future reader, including
the owner making downstream decisions on the strength of it. C —
rejected because discarding the experiment loses the two things it did
establish honestly (the reassessment-effect finding and the
result-survival finding); the problem is the causal framing, not the
underlying data collected.

## Consequences
(a) D-025's original hypothesis — context loss as a contributing cause
of Evidence Package's poor pilot results — remains neither confirmed
nor refuted by this experiment. A properly isolated test would need to
hold the assessment pass constant (e.g., the same evaluator re-reading
the same result set under both the old and new query, or scoring
against a fixed rubric) rather than comparing across two different
assessment sessions, as Milestone 4 did.
(b) This surfaces a broader methodological gap in how Evidence
Package's pilot-vs-re-run comparisons have been designed in this
project: first-pass interactive-assessment quality is itself a variable
that has not been isolated from the variable actually under test in any
experiment run so far.

## Validation
Confirmed by direct inspection of
`evidence_package/output/_m4_staging_20260813T114717.json` (recovered
raw result list from the original run) against
`evidence_package/output/evidence_run_20260815T150904.json` and the
in-session raw result capture from the 2026-08-15 re-run: AdIndex.ru's
URL present in both, at position 6/20 (old) and 9/20 (new).
`requests_used` and `search_backend.py` confirmed identical across both
runs by `git log`; the only code difference between the two runs is
Milestone 3's additive `build_search_query()` change (commit `bb549ee`),
already committed before Milestone 4 ran.

## Reversal condition
Resolved once a future experiment holds the assessment methodology
constant — the same evaluation pass reused across old/new queries, or a
fixed scoring rubric applied identically — while varying only the query
text, and reports a result under that controlled design. Redesigning
that experiment is out of scope for this record.

## Source
`context_layer/experiment_20260815_context_fix.json` (Milestone 4's
experiment artifact); `evidence_package/output/_m4_staging_20260813T114717.json`
(the recovered raw result set that made this audit possible); commit
`2b7c8a6` (Milestone 4, whose commit message's causal framing this ADR
corrects); ADR 0025 (the original context-loss hypothesis this
experiment attempted to test, quoted above rather than paraphrased).
