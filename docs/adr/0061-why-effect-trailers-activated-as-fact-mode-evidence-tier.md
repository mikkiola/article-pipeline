---
id: ADR-0061
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0061: Why:/Effect: commit trailers activated as a fact-mode evidence tier

## Status

Accepted. Implemented and unit-tested; not yet exercised by a real generated
post (see Confirmation & Revisit) — same category of record as ADR-0059 at
its own time of writing.

## Context & Constraints

ADR-0057 (2026-09-25) found 8 of 82 commits, all from a single calendar day,
carrying a `Why:`/`Effect:` commit-body trailer across `article-pipeline` and
`collector`, and declined to accept the convention as Evidence for the
LinkedIn fact-mode prompt. Its Decision point 4 set the activation condition
deliberately: not a fixed day count or percentage, but the owner's own
judgment once real history had accumulated, verified by a real-artifact test
rather than a coverage figure alone.

ADR-0059 (2026-09-29) fully superseded ADR-0057 for a different reason
entirely — it replaced the fact-mode prompt's reasoning structure (facts-only
→ five-step evidence-grounded reasoning) — and said nothing about commit
trailers; `[B-058]`'s subsequent implementation (through commit `e582b8c`,
2026-09-30) rebuilt `_build_fact_prompt()` against ADR-0059 without touching
Collector's `%b` capture, which still did not exist. ADR-0057 point 4's own
question — are `Why:`/`Effect:` trailers now Evidence? — was therefore left
open, not resolved, by ADR-0059's full supersession: nothing in ADR-0059 or
its implementation addresses it either way.

A re-measurement on 2026-10-01, reproducing ADR-0057's exact method
(`git log --since=... --pretty=format:'%b'`, matching `^Why:`/`^Effect:` line
starts) over both a 14-day and a 30-day window in both repositories, found:

| | article-pipeline | collector | total |
|---|---|---|---|
| commits, 14-day window | 69 | 14 | 83 |
| commits, 30-day window | 101 | 34 | 135 |
| qualifying (either window — identical result, no commit before 2026-09-25 carries a trailer) | 36 | 3 | 39 |

The 39 qualifying commits span four distinct calendar days — 2026-09-25
(14), 2026-09-26 (7), 2026-09-29 (5), 2026-09-30 (13) — with a gap on
2026-09-27/28, and in `collector` specifically only the first of those four
days. The owner judged this sufficient (her own prior estimate was 10-15;
the real count is 2.5-4x that). This is the real-artifact verification
ADR-0057 point 4 asked for, applied to the activation decision itself, not
yet to a generated post (see Confirmation & Revisit).

## Decision

1. **Why:/Effect: commit trailers are now Evidence for the fact-mode
   prompt**, resolving ADR-0057 point 4's deferred question — not reopening
   ADR-0059's own, separate reasoning-structure decision, which this ADR
   leaves untouched.

2. **Collector (`tier0_scan.py`) captures each commit's trailer via a
   second, `--numstat`-free `git log` call**, not by adding `%b` inline to
   the existing single-line header format: `%b` can itself contain embedded
   newlines, which the existing parser's "a non-`COMMIT_SEP`-prefixed line is
   a `--numstat` triple, or silently skipped if it isn't" heuristic would
   have swallowed without ever raising. The body fetch's own output stream
   has no `--numstat` lines in it at all, so there is nothing to confuse a
   body continuation line with. `WHY_RE`/`EFFECT_RE` extract the first
   `^Why:`/`^Effect:` line (same matching this ADR's own measurement used);
   absent trailers leave `why`/`effect` as `None`.

3. **`daily_brief.py`'s `SCHEMA_VERSION` moves 2 → 3.** Each
   `commit_messages` object gains `why`/`effect` (`None` when absent).
   `strategy_layer/adapters/collector.py`'s `DAILY_BRIEF_SCHEMA_VERSION`
   moves with it — a schema-2 brief is not interpreted (same fail-closed
   precedent a pre-schema-2 brief already had), not read as schema-3-minus-
   evidence.

4. **The Author side adds `commit_evidence`, a new field threaded alongside
   `commit_messages`** (`strategy_layer/adapters/collector.py`'s adapter →
   `AuthoringContext.commit_evidence` → `linkedin_verdict_reader.py`'s
   per-repo and top-level — deduplicated by `sha`, not subject text, since a
   `sha` is always unique while two commits can share a subject) — not a
   change to `commit_messages`' own shape. `commit_messages` keeps meaning
   exactly what it meant before this ADR (a flat subject-text list); only a
   commit that actually carries a trailer appears in `commit_evidence`.

5. **`_build_fact_prompt()`'s `build_clusters()` adds two new fact kinds**,
   `FACT_KIND_STATED_WHY` ("stated reason (Why: trailer)") and
   `FACT_KIND_STATED_EFFECT` ("stated effect (Effect: trailer)"), one fact
   per trailer line a commit actually has — kept visibly distinct from
   `FACT_KIND_SUBJECT` so the model (and `FINAL EVIDENCE CHECK`) can always
   tell an author-stated reason apart from a bare commit subject with none.
   A commit's stated-reason/stated-effect fact is never evidence for any
   other commit, even one in the same selected cluster.

6. **The FACT step's prior blanket "no reason, no consequence" is narrowed**,
   not removed: a commit with its own stated-reason/stated-effect fact may
   have it stated as that commit's own reason/effect; a commit without one
   is governed by the prohibition exactly as before. The "what the data does
   and does not contain" section and `FINAL EVIDENCE CHECK` are extended with
   the matching text, naming the failure mode explicitly: never infer a
   reason from a bare subject, and never borrow one commit's trailer for
   another's.

7. **ADR-0059's five-step structure, step order, and reasoning contract are
   unchanged.** This ADR extends what Evidence the FACT step and
   `FINAL EVIDENCE CHECK` may draw on; it does not touch TENSION, DESIGN
   INSIGHT, PERSONAL POSITION, RELEVANT PROBLEM, the automation-only-day
   guard, or identity continuity.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Change `commit_messages`' own shape to carry why/effect instead of adding `commit_evidence`. | Rejected — `commit_messages` is read in several places as a flat subject-text list (the mode heuristic, the flat top-level dedup, `build_clusters`' subject facts); changing its element type to a richer object would have forced every one of those call sites to change for a feature most of their callers don't need. A parallel, narrower field was the smaller, more targeted change. |
| B. Embed `%b` directly in `tier0_scan.py`'s existing single-line `git log` format string. | Rejected — concretely breaks: the existing parser treats every non-`COMMIT_SEP` line as a `--numstat` triple or silently drops it, and `%b` can contain its own newlines. A second, `--numstat`-free call removes the ambiguity instead of teaching one parser two incompatible line grammars. |
| C. Chosen — additive `commit_evidence` field, second git-log call, two new fact kinds, narrow prompt-text exception. | Reuses ADR-0059's five-step structure and existing citation verification (`verify_cited_facts`) unchanged — a new fact kind is automatically covered by the existing "cited IDs must belong to the offered cluster" check, no new verification code needed there. |
| D. Treat this as a reopening of ADR-0059's reasoning-structure decision. | Rejected — ADR-0059 decided a different question (how reasoning is structured); this ADR decides a question ADR-0059 never addressed (whether a specific new data source is Evidence at all). Keeping them as separate ADRs keeps each one's own scope legible. |

## Consequences

- Collector's weekly/manifest path (`classify.py`, `generate_outputs.py`,
  `refresh.py`) is untouched — confirmed by a direct search of every
  consumer of `tier0_scan`'s fields before this change; none of those three
  files read `subject`/`commit_messages`/`SCHEMA_VERSION` at all.
- `_build_idea_fallback_prompt()` (ADR-0044) is untouched — it never reads
  `commit_evidence`.
- A schema-2 `daily_brief` (written before this ADR) is not interpreted by
  the adapter going forward, same as a pre-schema-2 brief already was — no
  migration path was built for old on-disk files, since none are a live
  input to a future run.
- `docs/ARCHITECTURE.md`'s Author and Strategy Layer rows are updated in the
  same change as this ADR (see their own entries for exact test counts and
  commit SHAs).

## Confirmation & Revisit

Confirmed by construction: Collector's `tier0_scan.py`/`daily_brief.py` test
suites (28 tests, both files) and article-pipeline's `author/` (110 tests)
and `strategy_layer/` (101 tests) suites all pass, including new coverage for
the second git-log call's body capture, trailer extraction, schema-3
passthrough, `commit_evidence` deduplication, and the new fact kinds'
presence/absence in the rendered prompt (`author/test_daily_linkedin_author.py`,
`author/test_linkedin_verdict_reader.py`, `author/test_authoring_context.py`,
`strategy_layer/adapters/test_collector.py`,
`strategy_layer/adapters/test_metadata_whitelist.py`,
`author/test_no_message_bypass.py`). `import-linter`'s Anti-Corruption-Layer
contract and `scripts/check-strategy-layer-boundary.sh` both still pass
unchanged.

**Not confirmed:** a real end-to-end run — a real `Why:`/`Effect:`-bearing
`DailyBrief`, a real model call, and the resulting post checked against its
source commit trailers for accuracy, per ADR-0057 point 4's own stated
verification bar ("a good, verifiable post, not a high `Why:` coverage
figure"). This step was deliberately not taken in this session: it requires
a real, billable Anthropic API call
(`ANTHROPIC_API_KEY_DAILY_AUTHOR`, unset in this session's environment
regardless), which this project's own `strategy_layer/run_linkedin_pilot.py`
already treats as something "not invoked without explicit authorization,"
consistent with this project's standing rule against spending real money on
an LLM call without the owner's explicit go-ahead first. Revisit this
confirmation once that run has been made and the resulting post checked
against its source trailers, the same way `[B-058]`'s own checkboxes tracked
ADR-0059's real-post confirmation separately from its implementation.

## Source

Owner decision, 2026-10-01, following a re-measurement of commit-body
`Why:`/`Effect:` trailer coverage across `mikkiola/article-pipeline` and
`mikkiola/collector`, reproducing ADR-0057's own 2026-09-25 method over both
a 14-day and a 30-day window.
