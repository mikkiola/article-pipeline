---
id: ADR-0057
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0057: Commit-body Why:/Effect: trailers are not yet accepted as Evidence; facts-only publication stays in force

## Status

Accepted.

## Context & Constraints

`author/daily_linkedin_author.py`'s `_build_fact_prompt()` has used a temporary
facts-only structure since 2026-09-24 (commit `eb7b003`). It forbids the model from
stating a reason, consequence, insight or lesson that the supplied data does not contain.
That structure deviates from ADR-0044's Narrative Bridge, and the decision on whether to
amend ADR-0044 is still pending; this ADR does not make it.

Commit messages in this ecosystem may now carry `Why:` and `Effect:` lines in the body,
following a global Claude Code commit-message rule the owner introduced on 2026-09-24.
Those lines are the only place in the data chain where a stated reason for a change could
exist. They do not reach the prompt today:

- Collector's scan (`collector/scripts/tier0_scan.py`) reads `%H`, `%aI`, `%an` and `%s`
  from `git log`; it does not read `%b`.
- The prompt receives commit subjects only and says so ("commit_messages are subject
  lines only ... The data has no commit bodies, no reasons ...").

A read-only measurement on 2026-09-25 covered the 14-day window in both
`mikkiola/article-pipeline` and `mikkiola/collector` (`git log --since="14 days ago"`, each
commit's body read with `git log -1 --pretty=format:'%b'`):

| | article-pipeline | collector | total |
|---|---|---|---|
| commits in window | 60 | 22 | 82 |
| commits with a line starting `Why:` and a line starting `Effect:` | 5 | 3 | 8 |

All 8 are dated 2026-09-25 (author date, UTC+7); the earliest is
`2026-09-25T16:17:33+07:00`. The other 13 calendar days of the window (2026-09-12 to
2026-09-24) contain none, including the 12 article-pipeline commits of 2026-09-24. The
case-sensitive and case-insensitive counts were identical. The same check confirmed that
`%b` does return trailer lines (`Why:`, `Effect:`, `Syncs:`, `Closes:`,
`Co-Authored-By:`); no git config in either repository strips them.

Constraint that motivates this record: without an explicit statement, a later session
that sees `Why:`/`Effect:` appear in new commits could reasonably assume they are already
fair material for the post, and change what the pipeline publishes without a decision.

## Decision

1. **Facts-only publication stays in force.** The temporary structure from 2026-09-24
   (`eb7b003`) is unchanged by this ADR.

2. **`Why:`/`Effect:` trailers are not accepted as Evidence for the LinkedIn post prompt.**
   Commit bodies may contain them, but the 2026-09-25 measurement (8 of 82 commits, all
   from a single day) does not show a reliable publication source yet. No new data reaches
   the prompt and Collector is not changed: no `%b` capture, no new field.

3. **The existing restriction is made explicit.** `_build_fact_prompt()`'s "What the data
   does and does not contain" section gains three statements: only information present in
   the supplied data may be used; the author's motivation, reason, consequence or lesson
   must not be inferred or invented from a commit subject, a diffstat or a file path,
   because a commit subject describes what changed and does not establish why; and if the
   data contains no reason, none may be stated, implied or hinted at. The prompt stays
   silent about `Why:`/`Effect:` trailers, since they are not part of what it may use.
   `_build_idea_fallback_prompt()` and `check_post_content()` are unchanged.

4. **Future verification is a real-artifact test, not a threshold.** When `Why:`/`Effect:`
   have accumulated enough real commit history — judged by the owner, not by a fixed day
   count or percentage — run one end-to-end test that uses them as explicit Evidence: add
   `%b` capture to Collector, pass `Why:`/`Effect:` into the Author prompt as a new
   Evidence tier, run the real pipeline, and evaluate the resulting post against the
   source commit bodies for accuracy and quality. The aim is a good, verifiable post, not
   a high `Why:` coverage figure. Separately and continuously, observe whether the
   `Why:`/`Effect:` commit convention keeps being followed in normal daily work; this is a
   standing observation, not a checkpoint with a deadline.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Accept `Why:`/`Effect:` as an Evidence tier now (Collector captures `%b`, the prompt receives them). | Rejected. 8 of 82 commits, all from one day, and 0 of the other 13 days: on most days the tier would be empty, so the post would depend on whether one convention happened to be followed that day. Not enough history to judge the quality of the lines either. |
| B. Change nothing; rely on the prompt's existing "say nothing about a reason" line. | Rejected. That line is correct but does not say that a commit subject is not grounds for inferring a reason, and it says nothing about newly appearing trailers. A later session could read the trailers as already usable. |
| C. Chosen — strengthen the existing restriction, keep the prompt silent about trailers, record the decision and the verification path. | Adds no capability and no data. Makes the "no inferred why" rule unambiguous at the prompt level and gives later sessions one place to read that trailers are deliberately excluded. |
| D. Define the readiness condition as a day count or a coverage percentage. | Rejected by the owner. Coverage over a window measures how often a convention was followed, not whether the resulting post is accurate; the test that matters is one real post checked against its source commits. |

## Consequences

- Published posts are expected to be constrained as before (the new lines restate and
  sharpen a rule the prompt already had). This has not been checked against a live model
  call: the tests cover prompt text only, and no post was generated for this change.
- `Why:`/`Effect:` lines written in commits from now on have no effect on any post until a
  later ADR accepts them as Evidence.
- Enabling them later needs at least Collector `%b` capture and a new Evidence tier in
  the Author prompt (Decision 4). What else it touches — for example how a body would be
  carried through Collector's brief schema and Strategy Layer's `commit_messages`
  handling — was not investigated here, and nothing is designed.
- ADR-0044 is not amended, and whether facts-only replaces it is still pending the first
  real post.
- Out of scope and untouched: Collector, `_build_idea_fallback_prompt()`,
  `check_post_content()`, `publication_registry/`, `linkedin_publisher/`, the workflow
  YAML, and the older v1 templating path (`story_builder.py` / `channel_author.py`).

## Confirmation & Revisit

Confirmed by construction: `author/test_daily_linkedin_author.py` asserts that the three
new statements are present in the built fact prompt, that the prompt contains neither
`Why:`, `Effect:` nor the word "trailer", and that the idea-fallback prompt does not gain
the new text; the existing suite passes unchanged.

Not confirmed: the behavior of a real generated post under the new wording.

Revisit when the owner judges that `Why:`/`Effect:` history is sufficient (Decision 4).
Accepting them as Evidence would be a new ADR extending this one, not an edit to it.

## Source

Owner decision, 2026-09-25, following the 2026-09-25 read-only measurement of commit-body
`Why:`/`Effect:` coverage across `mikkiola/article-pipeline` and `mikkiola/collector`.
