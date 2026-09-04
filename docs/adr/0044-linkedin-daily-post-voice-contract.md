---
id: ADR-0044
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0044: LinkedIn Daily Post Voice Contract

## Status

Accepted.

## Context & Constraints

`author/daily_linkedin_author.py` (added session 2026-09-03, see
`docs/adr/0043-author-mvp-single-source-pilot.md`) generates one
LinkedIn post per day from a `DailyBrief` via a single LLM call. Its
current `STYLE_CONSTRAINTS` prompt text states general register rules
(no motivational language, keep FACT/IDEA/HYPOTHESIS distinct, never
invent evidence) but has no canonical, reviewable specification of
post structure, length, forbidden vocabulary, the evidence-citation
tiers, or the causal-chain requirement that numbers must be shown, not
just stated as a conclusion. That specification currently exists only
informally, drawn from the owner's own sample post plus two external
AI documents produced and cross-checked across sessions 2026-09-02,
2026-09-03, and 2026-09-04.

Per `docs/CONSTITUTION.md`'s own scope rule, this content-voice
specification cannot live in `docs/CONSTITUTION.md` (governs agent
behavior, not product content) and does not belong as permanent prose
in `docs/ARCHITECTURE.md` (states current implementation status, not
a specification's full text) or `docs/ROADMAP.md` (sequencing only).
An ADR is the correct home per this project's own governing rule (see
`mikkiola/tooltempest`'s `docs/reference/documentation-rules.md`,
CONSTITUTION.md section): "it belongs ... in an ADR as the decision
that produced it."

## Decision

The following is adopted as the LinkedIn daily post voice contract.
Prompt builders in `author/daily_linkedin_author.py`
(`_build_fact_prompt`, `_build_idea_fallback_prompt`) implement this
content as their specification — tracked separately as an
implementation task, see `docs/BACKLOG.md`'s `[B-058]`.

- **Structure:** Narrative Bridge 30/40/30 + hook + CTA + evidence
  links.
- **Length:** 150-250 words, max 3 sentences/paragraph.
- **Voice:** first person, active voice, concrete images, no
  hashtags, 0-1 emoji (self-deprecating only).
- **Forbidden:** metadiscourse openers, empty abstractions
  (approach/framework/level/process/strategy), AI clichés
  (delve/tapestry/revolutionize/game-changer/low-hanging fruit/etc),
  nominalizations, hedge words.
- **Causal chain rule:** numbers come from `DailyBrief`, never
  invented; the post must show the chain (e.g. N repos -> X hours
  each -> automated -> Y minutes), never state the conclusion
  directly.
- **CTA:** one open question, in-body, no direct pitch.
- **Evidence:**
  - L1 internal — always included, sourced from `DailyBrief`.
  - L2 public link — only if the repo is public per a live `gh repo
    view` check; silently omitted if private or the check fails, no
    apology line.
  - L3 market signal — emerges from reaction, never fabricated.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| **A. Hidden reasoning, one conclusion surfaces** — the model performs the causal reasoning internally and the post states only the resulting insight, with no visible chain of numbers. | Rejected — the reader cannot verify or independently judge the claim; it reads as an assertion, not evidence, and risks producing exactly the "false certainty" and unverifiable specifics `STYLE_CONSTRAINTS` already prohibits. |
| **B. Chosen — explicit numbered causal chain.** | The chain itself (N repos -> X hours each -> automated -> Y minutes) is the evidence: it lets a reader check each step against `DailyBrief`'s real numbers, keeps the post's central claim traceable to data rather than to model assertion, and matches this project's existing "never invent evidence" constraint at the structural level, not just as a prompt-level warning. |

## Consequences

- `_build_fact_prompt` and `_build_idea_fallback_prompt` in
  `author/daily_linkedin_author.py` do not yet implement this
  contract — the file's current `STYLE_CONSTRAINTS` text is narrower
  than this decision. Closing that gap is `docs/BACKLOG.md`'s
  `[B-058]`, not part of this ADR.
- The L2 public-link evidence tier introduces a new runtime dependency
  on a live `gh repo view` check at generation time — not yet present
  in `call_model()` or the prompt builders. Its failure/omission path
  (silent, no apology line) is part of this contract and must be
  implemented as stated, not approximated.
- Any future revision to structure, length, forbidden vocabulary, or
  the evidence tiers is a changed decision under Immutable Lineage
  (`docs/adr/0011`) — a new ADR superseding this one, not an edit to
  this file or to `STYLE_CONSTRAINTS` alone treated as the source of
  truth.

## Confirmation & Revisit

Not yet validated by implementation — this ADR records the accepted
specification; `[B-058]` tracks building it into the actual prompt
builders and validating generated posts against it. Revisit if a real
generated post cannot satisfy the causal-chain rule from a given
day's `DailyBrief` (e.g. too little activity to show a chain — see
`idea_fallback` mode's existing purpose), or if the `gh repo view`
live-check proves unreliable enough in practice to need a different
L2 mechanism.

**Source.** Sessions 2026-09-02, 2026-09-03, 2026-09-04; the owner's
own sample post plus two external AI documents, cross-checked across
those sessions.
