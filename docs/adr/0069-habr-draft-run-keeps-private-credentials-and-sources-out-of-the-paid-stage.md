---
id: ADR-0069
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0069: The Habr draft run keeps private sources and the broad GitHub token out of the paid stage

## Status

Accepted on 2026-10-15 as a decision. Not yet confirmed by a real run. Point 2
was revised on 2026-10-16, before this ADR was first committed, by the owner's
decision recorded in ADR-0070 (the five-category identity classification was
replaced by an author check).

## Context & Constraints

The Habr draft path (ADR-0071) sends repository content to a model API and
produces text meant for a public platform. Facts bound the design:

- The runtime workflow in the private runtime repository creates one GitHub App
  installation token over six repositories (private ones included) and passes it
  to the Python process (`GITHUB_APP_TOKEN`, ADR-0056 point 6). The integrity
  check needs that breadth; fragment retrieval does not.
- Collector scans private repositories; the owner decided (2026-10-15) that
  only approved public repositories may supply code, from a specific commit SHA.
- The Anthropic SDK retries requests by default (`DEFAULT_MAX_RETRIES = 2` in
  the installed 0.105.2 source), and billing of retried requests is not
  established.
- Unset calibration values (Q threshold, Habr rule 3 numbers) are owner policy
  (ADR-0071 point 6).

## Decision

1. **Two stages.** Stage 1 holds the broad token, makes no model call and
   fetches no fragments; it validates the daily brief and passes forward only
   integrity-valid, allow-listed, `main`-branch, source-cleared units. Stage 2
   holds a separate short-lived read-only token for `article-pipeline`, `radar`
   and `tooltempest` and the Habr API key; it never holds the broad token.
   Registry-data writes keep the existing default-token mechanism; the narrow
   token is never used for writes. No PAT and no new permanent secret.
2. **Allow-list with clearance.** Each entry is `repo@branch` and is unusable
   until the owner records a content-safety check and an authorship check. A
   fragment is admitted only when its commit's author is an owner identity
   (ADR-0070 point 3).
3. **Two modes.** `production` starts no paid call while a mandatory value is
   unset. `calibration` is one bounded round with recorded owner approval, never
   emits the ready outcome and never corrects on an unapproved threshold.
4. **Pre-call spend guard, best-effort.** `C_est = (1 + max_retries) *
   (input_tokens_estimate * price_in + max_tokens * price_out) / 1_000_000`,
   with `input_tokens_estimate` the UTF-8 byte count of all billable input text.
   A call whose estimate exceeds the remaining budget is not made. The limit is
   reported as best-effort, never as a guaranteed maximum.
5. **Output safety.** Generated text is scanned before it is saved, logged or
   judged; the model's raw response never appears in an exception or log; commit
   text and code are declared untrusted in every prompt.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. One process, one broad token, filter by code | Not chosen. A defect in a filter would put private-scope credentials next to the paid call and the fragment fetch. |
| B. A personal access token for fragments | Not chosen. Owner decision: no PAT, no new permanent secret. |
| C. Post-hoc spend check only | Not chosen. Money may be spent before the check fires. |
| D. Chosen: two stages, narrow token, allow-list, two modes, pre-call guard | Keeps private scope away from the paid stage and makes missing configuration observable without a paid call. |

## Consequences

- The workflow has two Python steps and an intermediate file in the runner's
  temp directory (not committed). The runtime workflow lives in another
  repository; adding it is a push the owner approves. A reviewed draft is
  `habr_draft/runtime_workflow.example.yml`.
- The input-byte estimate is a proxy, not a tokenizer measurement and not a proven
  upper bound; the guard can both over- and under-estimate the real bill.
- Until the owner sets the numeric values and clears the sources, a production
  run ends as `SYSTEM_FAILURE` with failure kind `missing_configuration`, and no
  topic is drawn from an uncleared repository.

## Confirmation & Revisit

Not confirmed. Confirmation requires a real calibration run whose saved record
shows the stages' separate tokens (workflow log), the allow-list applied, the
budget report and a committed record with its notification.

Revisit when the App token's permission input is verified in the pinned action
version, when the owner changes the allow-list, or when the SDK retry behavior
changes.

**Source.** Owner decisions of 2026-10-15 (code sources, credentials, modes,
budget guard); reading of the runtime workflow file and of the action's README
the same day. No external AI contributed to the decision.
