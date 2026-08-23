---
id: ADR-0030
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0030 — English-first cascading search strategy

## Status

ACTIVE. Decision made; implementation not yet done (see Consequences).

## Context & Constraints

Two independent pieces of evidence, from different sessions, both show
mixed results for either language alone — neither language dominates:
(1) the 2026-08-13 English-vs-Russian comparison found 3 of 5 Claims
improved on English, 1 improved imprecisely, 1 got worse; (2) the
2026-08-16 D-025 paired experiment (Russian control vs. context-
enriched treatment) found a similar mixed pattern (mean Δ = 0.2, "no
clear signal" per Section 7's thresholds), with one regression traced
to a concrete, explainable mechanism (a polysemous tag drifting the
query into an unrelated domain — see the new atom-tag-disambiguation
BACKLOG item). Given neither language reliably outperforms the other
across all Claims, option B (always both) guarantees doubled budget
even where the first language already succeeds, wasting requests.
Option C's quota is arbitrary — it doesn't respond to which Claims
actually need the second language. Option D spends the second request
only where the first language's own measured result is weak, keeping
the existing per-Claim budget ceiling (2 requests/Claim) intact rather
than raising it.

The cascade's score threshold (< 2 on the 0/1/2 rubric) is currently
based on a rubric still marked DRAFT (context_layer/D-025_experimental
_brief_DRAFT.md) — if that rubric's scale or content changes, this
cascade's threshold must be revisited, not silently inherited.
Search budget must not exceed the existing SPEC.md limits (2 requests/
Claim, 20/run) — the second cascade attempt uses the SAME per-Claim
budget slot, not an additional one.

## Decision

English is the primary search language for Evidence Package. If the
English-language search result for a given Claim scores below 2 ("not
strong support") on the D-025 experimental rubric (context_layer/
D-025_experimental_brief_DRAFT.md, Section 5), a second search attempt
is made in Russian for that same Claim only. The Claim's final score is
the better of the two attempts. This is a per-Claim cascade, not a
fixed language quota across a run.

## Alternatives & Rationale

A — Russian only (status quo before this decision). B — both languages
always, for every Claim (doubles the search budget). C — fixed split
(e.g. some Claims English, some Russian, by quota, not by measured
result quality). D — English-first cascade, Russian only as a
per-Claim fallback when English scores below 2 (chosen).

D.

A — status quo doesn't use available evidence that English often
finds better sources for internationally-published/technical topics.
B — doubles budget/cost unconditionally, even when unnecessary. C —
arbitrary quota unresponsive to actual per-Claim result quality.

## Consequences

NOT YET IMPLEMENTED. Extending evidence_package/driver.py's
QUERY_TRANSLATIONS_RU_EN table to cover treatment-query text (not just
control) and all future Claims (not just this pilot's 5), and wiring
the score-based cascade logic into build_search_query()/run_searches(),
is separate future implementation work — tracked in docs/BACKLOG.md.
This ADR records the decision, not the implementation.

## Confirmation & Revisit

Not yet validated in production — informed by two prior experimental
comparisons (2026-08-13 English-vs-Russian pilot; 2026-08-16 D-025
paired experiment), neither of which used the cascade design itself
(both compared full independent language runs, not per-Claim
fallback). The cascade's actual effectiveness is untested until
implemented and run.

Resolved/reconsidered if a future measurement shows the cascade
underperforms either single-language approach, or if the DRAFT
rubric's threshold changes materially.

**Source.** 2026-08-13 English-vs-Russian comparison (evidence_package/output/
_m4_staging_en_20260813T124320.json); 2026-08-16 D-025 paired
experiment (Russian run); docs/BACKLOG.md's atom-tag-disambiguation
item (found via the same experiment).
