---
id: ADR-0059
status: Accepted
supersedes: [ADR-0044, ADR-0057]
superseded_by: null
source_type: verbatim
---

# ADR-0059: Fact-mode post generation uses a five-step evidence-grounded reasoning pipeline with a personal position

## Status

Accepted. Matching ADR-0058's own precedent: this is a reversible, evidence-tested design,
validated through a standalone trial process against real fact clusters from this
repository's own commit history, not yet exercised by a real production post.

## Context & Constraints

ADR-0057 (2026-09-25) restricted the fact-mode prompt to state only facts directly supported
by a `DailyBrief`, forbidding any inference of motivation, reason, or consequence. This was
written before any real generated post existed to evaluate, to solve a narrower problem:
preventing the model from inventing unverified motive claims and presenting them as fact.

Once real posts were generated and reviewed (2026-09-27, 2026-09-28 scheduled runs), the
owner found the restriction broader than intended in practice: it blocked all reasoning over
facts, not only fact-invention, producing posts that read as changelogs.

ADR-0044 (2026-09-04) specified a different, never-implemented structure for fact-mode
(Narrative Bridge 30/40/30 + hook + CTA + evidence tiers) — `[B-058]` tracked its
implementation but all four of its checkboxes remain unchecked; fact-mode's actual prompt has
always used ADR-0057's facts-only structure instead.

A third, older specification exists in `[B-057]` (2026-09-03, `docs/BACKLOG.md`): the
originally-intended fact-mode pipeline, `FACT -> EMERGENT PROPERTY -> INVERSION -> COMMERCIAL
HYPOTHESIS`, implemented once and then deliberately removed on 2026-09-24 alongside
ADR-0057's facts-only pivot. A permanent regression test in
`author/test_daily_linkedin_author.py` (~lines 171-174) currently asserts the strings
`EMERGENT PROPERTY`, `INVERSION`, `COMMERCIAL HYPOTHESIS`, `emergent_property`, `inversion`,
and `commercial_hypothesis` must never reappear in the fact-mode prompt — this test enforced
ADR-0057's now-superseded requirement correctly; it is not a bug, and its obsolescence is a
direct consequence of this ADR.

A standalone trial process (outside this repository, in a now-deleted, archived sandbox)
tested a revised reasoning contract against real fact clusters from this repository's own
commit history, iterating through five stages of refinement, each driven by a concrete
failure found in the previous stage's real model output:

1. An initial FACT/EMERGENT PROPERTY/INVERSION/PERSONAL THESIS/COMMERCIAL PAIN structure
   produced generic, changelog-adjacent thought-leadership text — the EMERGENT PROPERTY
   instruction's own framing ("a property that would hold regardless of this particular
   code") rewarded genericness by construction.
2. Replacing EMERGENT PROPERTY/INVERSION with TENSION/ARCHITECTURAL INSIGHT/PERSONAL
   POSITION/RELEVANT PROBLEM, run three independent times on one identical prompt, produced
   text with real specificity but let the model infer unstated causal/design relationships
   between co-occurring commits (e.g., asserting one commit was "needed to fix" a gap another
   commit's absence caused).
3. Adding an explicit prohibition against inferring causal or design intent from mere
   co-occurrence fixed the over-reach, but the fix also caused three independent calls to
   converge on the same tension — the TENSION instruction's own example anchored the model
   onto one reading, the same failure mode as stage 1.
4. Splitting TENSION generation across three distinct analytical lenses (SYSTEM / BOUNDARY /
   DESIGN CHOICE), each explicitly shown prior lenses' findings and required to report a
   genuinely distinct underlying observation (or say so plainly via a `NO_DISTINCT_TENSION`
   fallback rather than manufacture a rephrased duplicate), produced three real,
   substantively different engineering observations from one identical fact cluster.
5. A further identity-trajectory trial confirmed the mechanism also needs the author's own
   real recent post history and a compact identity-state (distinguishing `emerging_positions`
   from `core_positions` — a position is never promoted to core based on a single post) to
   produce a post that advances a cumulative professional identity rather than an isolated
   thought. This stage also surfaced two real defects, both now fixed in the contract below:
   (a) a day with only automated, scheduled output (no manual engineering decision) caused
   the model to invent an engineering "discipline" narrative around the automation's own
   commit shape — fixed by an explicit automation-only-day guard; (b) even after every
   upstream constraint held, the final synthesized post prose itself invented an unstated
   factual claim ("nobody had a way to notice except reading closely and comparing dates")
   that passed every prior check because none of them inspected the finished narrative text —
   fixed by a final evidence-check step applied to the completed post before it is returned.

## Decision

1. **This ADR supersedes ADR-0057 in full, and supersedes ADR-0044 only for fact-mode.**
   ADR-0057's facts-only boundary applied to fact-mode generation exclusively, so its full
   supersession is unambiguous. ADR-0044's Narrative Bridge voice contract governed both
   `_build_fact_prompt()` and `_build_idea_fallback_prompt()` — this ADR's reasoning contract
   (Decision point 4 below) replaces ADR-0044 only for the fact-mode path
   (`_build_fact_prompt()`). ADR-0044 remains the active, normative specification for
   `_build_idea_fallback_prompt()` and idea_fallback mode generally, until a future decision
   addresses that mode specifically. Both ADR-0044 and ADR-0057 remain unchanged as historical
   records (Immutable Lineage); only ADR-0044's frontmatter reflects a partial-supersession
   note, and ADR-0057's frontmatter reflects full supersession.

2. **What is preserved from ADR-0057, unchanged:** a post must never state, imply, or invent
   a fact about the real product, the developer's actual historical motivation, or the
   external world (market, users, competitors) beyond what the supplied `DailyBrief` fact
   cluster contains. Co-occurrence of two commits in the same batch is never evidence of a
   causal or design relationship between them — state only that both are true at once, never
   that one explains, caused, or was built for the other.

3. **What is lifted from ADR-0057:** the blanket prohibition on any reasoning over facts is
   replaced with a narrower rule — reasoning is permitted, and required, but must be
   explicitly framed as interpretation, thought experiment, or preference, never asserted as
   established fact.

4. **The fact-mode reasoning pipeline becomes:**
   - **FACT** — restate only what the fact cluster directly supports. No interpretation, no
     reason, no consequence.
   - **TENSION** — identify a concrete, specific gap, mismatch, asymmetry, or unresolved
     design question visible in the fact cluster itself. Must state the observation itself,
     not an inferred reason for it; must not infer that one commit was designed to detect,
     cause, enable, or respond to another absent an explicit statement to that effect in the
     facts.
   - **DESIGN INSIGHT** (supersedes `[B-057]`'s EMERGENT PROPERTY and ADR-0044's Narrative
     Bridge structure) — what the tension reveals about the kind of system or engineering the
     author values, framed explicitly as interpretation. Must preserve the exact object of
     the tension (no new actor, capability, failure mode, causal mechanism, or market
     behavior absent from the facts) and must not depend on an unstated design intent. Must
     pass a specificity test: if the sentence could be published about almost any project
     with a similarly-shaped commit, it fails and must be rewritten, not hedged.
   - **PERSONAL POSITION** — a present-tense engineering preference or design value the
     author could carry forward into other systems, explicitly framed as something today's
     work may strengthen, clarify, or cause the author to formulate — never as a claim about
     the historical motivation behind the actual commits. May be broader than what today's
     data proves; only the underlying FACT and TENSION must remain proven.
   - **RELEVANT PROBLEM** (supersedes `[B-057]`'s COMMERCIAL HYPOTHESIS) — a real-world
     problem or pain the position plausibly addresses, framed explicitly as an untested
     hypothesis, never as confirmed fact about any market, product, or user.
   - **FINAL EVIDENCE CHECK** — applied to the fully synthesized post text itself, not only
     the upstream reasoning fields, before it is returned: every factual or causal statement
     in the finished prose must be directly supported by the fact cluster or the author's
     real recent posts. Statements about absence of a capability, what "nobody"/"the
     team"/"the system" could or couldn't do, unstated causal relationships, conclusions
     about what work "really was" beyond the evidence, or unstated user/business/market
     impact must be rewritten conservatively or removed. This check does not constrain the
     personal position itself — the evidence requirement applies to claims about reality, not
     to the author's stated preferences.

5. **INVERSION (from `[B-057]`) is not restored.** The trial process found it consumed
   narrative space better spent on DESIGN INSIGHT/PERSONAL POSITION and, in practice, was
   always hedged away to nothing by the post's own closing ("nothing here suggests this is
   happening") without adding identity signal. Reconciling `[B-057]` and ADR-0044 by
   restoring both in full was explicitly rejected during the trial process — the two
   structures are not combined; this ADR's five-step-plus-check pipeline is the only
   structure fact-mode posts follow going forward.

6. **Identity continuity is part of the contract, not a separate later feature.** Generation
   should take, alongside today's fact cluster: the author's real recent published posts, and
   a compact identity state distinguishing `core_positions` (established, recurring across
   multiple posts) from `emerging_positions` (introduced once, not yet promoted). A position
   is never promoted to `core_positions` on the strength of a single post. The
   `identity_state` also tracks `recently_used`, `underdeveloped` (dimensions visible in the
   work but not yet publicly established), `open_threads`, and a short `trajectory`
   narrative — kept compact, not grown indefinitely; equivalent positions are merged, not
   duplicated.

7. **A day with no manual engineering decision behind it must not manufacture an engineering
   position.** If the day's fact cluster shows only the output of an automated, scheduled
   process with no accompanying manual work, the pipeline must recognize this and produce no
   personal position and no full post from it, rather than inventing a "discipline" narrative
   around the automated output's incidental shape. This guard's text exists in the trial
   prompt; its production form is `[B-069]` (see `docs/BACKLOG.md`), not shipped by this ADR.

8. **What the regression test in `author/test_daily_linkedin_author.py` enforced is
   obsolete, not wrong.** Its assertions that `EMERGENT PROPERTY`, `INVERSION`, `COMMERCIAL
   HYPOTHESIS`, and their JSON-key forms must never appear in the fact-mode prompt correctly
   encoded ADR-0057's now-superseded requirement. This ADR changes that requirement; the test
   will need updating when `_build_fact_prompt()` is rebuilt against this contract (tracked
   in `[B-058]`'s revision) — not fixed as part of this ADR itself.

9. **The exact machinery for separating FACT from interpretation in the published post's
   visible text (a dedicated field, an in-text marker, or another mechanism) is not decided
   by this ADR.** It is a separate, later design decision, filed as `[B-068]` (see
   `docs/BACKLOG.md`).

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| Keep ADR-0057's blanket prohibition; ship a wholly separate "idea post" type alongside unchanged fact-mode posts | Rejected — the goal is one daily post combining grounded fact and evidence-framed reasoning, not two parallel post types with different rules. |
| Restore ADR-0044's Narrative Bridge in full, on top of `[B-057]`'s FACT/EMERGENT PROPERTY/INVERSION/COMMERCIAL HYPOTHESIS | Rejected — never tested together, and the owner explicitly did not want both restored simultaneously; this ADR's five-step pipeline is the single reconciled structure. |
| Chosen — five-step pipeline (FACT/TENSION/DESIGN INSIGHT/PERSONAL POSITION/RELEVANT PROBLEM) plus a final evidence check on the synthesized post, with identity continuity and an automation-only-day guard | Validated through a five-stage real-data trial process, each stage fixing a concrete failure the previous stage's real model output exhibited; the only option with direct evidence of working as intended on this project's own real commit data. |

## Consequences

- `author/daily_linkedin_author.py`'s `_build_fact_prompt()` no longer matches this ADR's
  required structure and needs rebuilding — tracked by a revision to `[B-058]` (see
  `docs/BACKLOG.md`).
- `author/test_daily_linkedin_author.py`'s removal-assertion list (Decision point 8) will
  need updating once the prompt is rebuilt — not edited by this ADR.
- Identity continuity (Decision point 6) requires the production pipeline to supply real
  recent post text and a persisted identity state to the prompt at generation time — a new
  data dependency not present in the current `daily_publish.py`. This is implementation work,
  tracked separately, not performed by this ADR.
- The automation-only-day guard (Decision point 7) needs a production form — ideally a
  pre-call check in `daily_publish.py` that skips generation entirely (not just the
  prompt-level guard tested in the trial, which still spent one API call recognizing the
  automation-only day). Filed as `[B-069]` (see `docs/BACKLOG.md`).
- `docs/ARCHITECTURE.md`'s Author row will need a fact-sync update once the new prompt is
  built and validated against real posts — not part of this ADR's own sync (which corrects
  only the already-confirmed-stale clustering-exercised-by-a-real-post fact, unrelated to
  this ADR's own contract).

## Confirmation & Revisit

Not yet validated by production implementation — this ADR records the accepted reasoning
contract, proven through a standalone trial process on real repository data, not yet
exercised by a real scheduled post. Revisit once `[B-058]`'s revision is implemented and real
generated posts have been checked against this contract, per this project's TDD threshold for
a correctness-sensitive prompt change.

## Source

Owner decision, 2026-09-29, following an extended trial process (standalone sandbox,
archived by the owner as `article-pipeline-trial-archive-20260929.tar.gz`, not committed to
this repository); `[B-057]` (2026-09-03) as the historical record of the original
FACT/EMERGENT PROPERTY/INVERSION/COMMERCIAL HYPOTHESIS concept partially restored by this
decision; `docs/adr/0057` as the prior decision this ADR fully supersedes, and `docs/adr/0044`
as the prior decision this ADR supersedes for fact-mode only, remaining otherwise Accepted and
normative for `_build_idea_fallback_prompt()`.
