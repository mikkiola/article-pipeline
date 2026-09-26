---
id: ADR-0058
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0058: The fact prompt offers per-repository clusters of ID-tagged facts, and cited IDs are verified

## Status

Accepted. Experiment 1: a deliberately narrow, reversible change to how facts are grouped,
selected and cited. It does not change ADR-0057's inference boundary.

## Context & Constraints

The fact-mode prompt (`author/daily_linkedin_author.py`, `_build_fact_prompt()`) handed the
model one flat block for the whole day: every commit subject of every included repository,
a per-repository stats list, and cross-repository totals. The task that requested this
experiment reports that this produces changelog-shaped posts: a list of unrelated facts
followed by a generic question. The model had no single coherent thread to work from and no
permission to connect facts into one paragraph, even inside the facts-only boundary. This ADR
records the requesting task's diagnosis; the change has not been evaluated against a real
generated post.

Two facts about the data, verified in the code before deciding:

- `per_repo` entries in the DailyBrief-shaped dict carried only `name`, `commit_count`,
  `diffstat` and `files_touched`. Commit subjects existed only in a flat top-level list that
  `author/linkedin_verdict_reader.py` built by merging every included repository's messages and
  collapsing identical subjects across repositories. The per-repository attribution that
  Collector's adapter established (ADR-0056) was still present in each `AuthoringContext`
  and was discarded in this one reader.
- The model-response check, `validate_structured_response(response, mode)`, received only the
  mode. It could not know which clusters or fact IDs had been offered, and its production
  call in `linkedin_publisher/daily_publish.py` passed nothing else.

ADR-0057's boundary is a separate variable under test: the prompt must not state or infer a
reason, consequence, insight or lesson that the data does not contain. This experiment must
not loosen it, so that any change in post quality can be attributed to clustering,
selection and connection alone.

## Decision

1. **Cluster per repository, deterministically.** One cluster per repository with
   `commit_count > 0`; a repository with no commits forms no cluster and is not offered. No
   semantic, topic or keyword grouping of any kind.

2. **Stable fact IDs.** Each fact gets `{repo}:fact_{NN}` (zero-padded, 1-indexed). Facts are
   one per commit subject (that repository's own messages, in order, unreworded), then one for
   the repository's commit count, then one for its files-touched count (computed in code). No
   diffstat fact, because the prompt already forbids lines-changed figures as evidence. A
   `per_repo` entry with no `commit_messages` key, or a run with no cluster at all, raises
   rather than degrading to count-only clusters.

3. **Prompt shape.** The model sees only the clusters, not the flat cross-repository dump. It
   is told to select exactly one cluster ("select one repository whose cluster contains enough
   related facts to form a coherent post"; if several qualify, any one is acceptable; no
   evaluative criterion), to use only that cluster's facts, and that it may connect 2-3 of
   them into one connected paragraph. Connecting facts is expressly not permission to state
   why something was done, what it leads to or what it means.

4. **ADR-0057's wording is unchanged.** The sentence "It does not explain, interpret, or
   speculate", the three evidence-boundary statements added by ADR-0057, the "If the input
   does not contain a reason for a change, say nothing about a reason" bullet, and the
   no-reason/consequence/insight paragraph are quoted into the new prompt verbatim. Two
   pieces of surrounding wording changed only because the data shape changed: the old bullet
   saying commit messages "are not attributed to a repository" is replaced (it is no longer
   true, as ADR-0056 already noted), and the numbers rule now refers to the selected
   cluster's facts instead of cross-repository computed counts.

5. **New required response keys and a deterministic check.** `selected_cluster` and
   `supporting_facts` join `post` and `fact_or_product`. In fact mode,
   `validate_structured_response()` now also receives the `daily_brief` and calls
   `verify_cited_facts()`: `selected_cluster` must equal one of the offered cluster names, and
   `supporting_facts` must be a non-empty list of strings, each exactly equal to an ID of that
   selected cluster. Comparison is exact string match; there is no fuzzy or semantic matching.
   A failure raises `AuthorLLMError`, and fact-mode validation with no `daily_brief` also
   raises, so a caller that forgets to pass it fails closed instead of skipping the check.

6. **What the check proves, and what it does not.** It proves that the model cited only
   facts it was actually given, and only from the cluster it named. It does not prove that the
   post's prose is faithful to those facts, that the cited facts support what the post says,
   or that the listed facts are the ones the post used. A post can cite real IDs and still
   misstate them. `check_post_content()` (ADR numbers, greetings) is unchanged and remains the
   only content check on the prose itself.

7. **Scope this required.** The per-repository messages had to be added to each `per_repo`
   entry in `linkedin_verdict_reader.py` (the flat top-level `commit_messages` and `mode` stay
   as they were, because the idea-fallback prompt reads the flat list), and the real call
   site in `linkedin_publisher/daily_publish.py` had to pass the brief to the validator.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Keep the flat cross-repository list. | Rejected. It is the shape the changelog-like output is attributed to; leaving it makes the experiment impossible. |
| B. Cluster by topic or subject-line keywords or embeddings. | Rejected for this round. It needs a grouping mechanism with its own error modes, which would add a second variable to the experiment. Repository is the one grouping already present in the data. |
| C. Chosen: per-repository clusters, one selected, facts connectable, cited by ID and checked. | One variable changes (grouping, selection and connection). The check makes a citation mechanically verifiable, and the boundary stays as ADR-0057 fixed it. |
| D. Add a quality scorer, a second model pass or a ranking of clusters. | Rejected. More machinery and more variables; selection uses only a neutral sufficiency criterion. |
| E. Relax ADR-0057 so connected facts may carry a "why". | Rejected. That boundary is tested independently; conflating the two would make the result unreadable. |
| F. Check IDs without changing `daily_publish.py`. | Rejected. The validator cannot know the offered clusters without the brief; an optional argument nobody passes would leave the check off in production, and a required one would fail every run. |

## Consequences

- **Failure mode, traced in the real call sequence.** In `daily_publish.py` on the pass path
  the order is: model call, `validate_structured_response()`, `linkedin_client.publish_post()`,
  `registry_writer.write_record()`. A failed verification raises `AuthorLLMError` before
  publish and before any Registry write. This is pinned by tests that run `main()` with the
  real validator and assert that `publish_post` and `write_record` were never invoked, and a
  test that pins the sequence `validate, publish_post, write_record` on success. The workflow's
  "Commit and push Registry output" step has no `if:` condition, so it is skipped when the
  publish step fails. Not covered by that statement: on the gate-blocked path a block record is
  written before any model call exists, and the Strategy Layer verdict file is written before
  the model call on the pass path (that output directory is not committed).
- **A failed check means no post that day.** If the model omits the two new keys or cites an
  ID it was not given, the run fails closed and nothing is published. Whether the model does
  this reliably has not been measured; no live model call was made in this change.
- Repositories with commits but no messages (weekly-manifest data) would form count-only
  clusters; the daily path this prompt serves carries messages.
- L2 public-link lookups now run only for repositories that form a cluster.
- ARCHITECTURE.md's Author row and test counts describe the previous prompt and are not
  updated by this ADR.

## Confirmation & Revisit

Confirmed by construction, not by outcome: `author/test_daily_linkedin_author.py` (cluster
and ID construction, zero-commit exclusion, prompt shape and the unchanged ADR-0057 wording,
each rejection case, the fail-closed paths), `author/test_linkedin_verdict_reader.py`
(per-repository messages kept without cross-repository deduplication, flat fields
unchanged) and `linkedin_publisher/test_daily_publish.py` (the call-order tests, which were
also shown to fail when the validation is moved after `publish_post`).

Not confirmed: that clustering, selection and connection change the character of real posts;
that the model returns the new keys reliably. Revisit after real posts under this prompt have
been reviewed. If per-repository grouping proves too coarse, a topic-based grouping would be
a new ADR extending this one, not an edit to it.

## Source

Owner task, 2026-09-26, and its follow-up authorizing the widened file scope after the
per-repository attribution gap in `linkedin_verdict_reader.py` and the validator's call site
in `daily_publish.py` were found.
