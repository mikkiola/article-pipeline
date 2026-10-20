# Q rubric: infostyle criteria for a Russian technical draft

Materialized from the owner's `human-text` practice (Ilyakhov's infostyle).
This file is the rubric of the Q check's own prompt; it is not a scoring
engine and its score is not an objectively proven metric.

Assess the draft against these criteria. For each violation give the
criterion id, a severity (`minor` | `major`) and a short note naming the
place, without quoting more than a few words.

1. `facts_not_opinions` - facts and numbers instead of evaluations and
   promises ("reliable", "high-quality" with no data is a violation).
2. `one_thought_per_sentence` - a sentence carrying two thoughts joined by a
   comma is a violation.
3. `bureaucratese` - officialese where one plain word exists.
4. `ai_markers` - filler such as "в современном мире", "на сегодняшний день",
   "безусловно", "несомненно", "важно отметить", "в контексте", "в рамках
   данного", "комплексный подход", "синергия", "подводя итог"; an
   introductory sentence with no information ("Давайте рассмотрим X"); a
   conclusion that only restates the introduction; a list of exactly three
   one-sentence items; passive voice where active is possible.
5. `ambiguity` - a sentence that can be read in more than one way, or a
   hedge ("возможно", "при определённых условиях") without the condition
   named.
6. `claim_without_evidence` - an assessment with no fact behind it.

Score: an integer from 0 to 100, higher is better. 100 means no violations
found. The score is a judgment of this rubric only; it says nothing about
whether the text may be published.
