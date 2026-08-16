# 0031 — D-025 paired experiment: context-enrichment synthesis

## Status
ACTIVE (diagnosis + synthesis). Corrects/extends ADR-0025's original
hypothesis and ADR-0029's confound finding with a properly isolated
paired experiment (per ADR-0029's reversal condition).

## Decision
D-025's context-loss hypothesis is PARTIALLY CONFIRMED, with an
important qualification: query enrichment can help when the injected
context correctly reflects the atom's intended domain (Russian run,
Claims _01/_05: control found nothing relevant, treatment found
relevant sources), but the current raw-tag-injection design actively
harms results when a tag is polysemous/ambiguous (Claims _03/_04 in
BOTH language runs: the tag "доверие"/"trust" pulled search into an
unrelated domain — IT-security certification in Russian, finance/law/
security in English, more severely). This is not a diffuse or
unexplained risk — it is one specific, identified, repeatable failure
mechanism, isolated to how tags are injected into the query, not a
general flaw in the context-enrichment concept itself.

## Options
A — treat the mixed/negative mean Δ as refuting the context-loss
hypothesis, discontinue context enrichment. B — treat the isolated
tag-collision mechanism as the explanation for the negative results,
and pursue tag disambiguation as a targeted fix rather than abandoning
the approach (chosen). C — inconclusive, defer to a larger-sample
follow-up before deciding anything.

## Chosen
B.

## Why
The paired experiment (context_layer/experiment_20260816_D025_paired
.json), run per context_layer/D-025_experimental_brief_DRAFT.md's
resolved design (paired per-Claim comparison, fixed 0/1/2 rubric, new
control run in the same session — not the historical run), found:
Russian run mean Δ = 0.2 (no clear signal per DRAFT Section 7's
thresholds); English run mean Δ = -0.8 (negative signal, 3 of 5 Claims
regressed). Both regressions in the Russian run's worst case (_03) and
both of the English run's two worst regressions (_03, _04) trace to
the exact same word ("доверие"/"trust") carrying a different sense in
the atom's own context than in the domain the enriched query drifted
into. Separately, both language runs' CONTROL results (novelty+basis
only, no enrichment) were independently strong — English control
found peer-reviewed/institutional sources (arXiv, CMU SEI, ACM CHI)
for 3 of 5 Claims even without any enrichment. This means the
underlying search capability is not the limiting factor; the specific
mechanism of raw tag/wiki-link injection is. A single, repeatable,
mechanistically-understood cause explaining the negative results is a
materially different, more actionable finding than an unexplained
mixed result — it points to a scoped fix (tag disambiguation, already
tracked in docs/BACKLOG.md), not a redesign or abandonment of the
context-enrichment concept.

## Constraints
This finding does not change the Evidence Package `verified` criterion
(inherited from ADR-0025/0029). It does not resolve the DRAFT's
still-open calibration-approach question. It does not establish that
tag disambiguation alone is sufficient to produce a positive signal —
only that it targets the one concretely identified failure mechanism
found so far; other undiscovered failure modes may still exist in a
larger sample.

## Rejected
A — rejected because it would discard a result that the data itself
explains mechanistically; treating "context enrichment doesn't work"
as the conclusion would misrepresent what was actually found (a
specific, fixable defect, not a general failure of the concept). C —
rejected because the mechanism is already identified and actionable;
deferring to a larger sample before attempting the known fix wastes
the diagnostic value already obtained.

## Consequences
docs/BACKLOG.md's atom-tag-disambiguation P1 item is the direct
follow-up action from this finding. Until that fix is implemented and
re-tested, context-enriched queries should be treated as carrying a
known regression risk specifically tied to polysemous tags — this is
not a reason to disable context enrichment, but a reason to prioritize
the disambiguation fix before treating context-enriched results as
reliably better than control. ADR-0030's English-first cascade
decision is unaffected by this finding — it operates at the language-
selection level, independent of whether context enrichment is used
within either language's query.

## Validation
Confirmed by direct experiment — context_layer/experiment_20260816_
D025_paired.json, paired design per context_layer/D-025_experimental
_brief_DRAFT.md (Sections 4, 5, 7), 20 total search requests across
both language runs, full-page reads used for scoring where relevant
(not just snippets).

## Reversal condition
Resolved once tag disambiguation is implemented and a follow-up paired
experiment (same design) shows the _03/_04-type regression no longer
occurs, and/or shows a clearly positive mean Δ once the identified
failure mechanism is removed.

## Source
context_layer/experiment_20260816_D025_paired.json (this experiment);
context_layer/D-025_experimental_brief_DRAFT.md (the experimental
design this ADR's finding is based on); ADR-0025 (original hypothesis);
ADR-0029 (confound correction, reversal condition this experiment
satisfies); docs/BACKLOG.md's atom-tag-disambiguation item.
