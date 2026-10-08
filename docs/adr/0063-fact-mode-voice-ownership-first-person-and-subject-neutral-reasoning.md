---
id: ADR-0063
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0063: Fact-mode first-person voice is owned by this record, and its reasoning steps analyze the work, not "the author"

## Status

Accepted. A narrow clarification of which record owns one requirement for
fact-mode. It does not reopen, restate or amend the five-step reasoning
contract, and it does not change the text of any earlier ADR.

## Context & Constraints

ADR-0059 supersedes ADR-0044 for fact-mode only. It does so through its
reasoning contract (the five steps and the final evidence check) and through
replacing the Narrative Bridge structure. It says nothing about voice or
grammatical person in the published fact-mode post.

ADR-0044's Voice bullet ("Voice: first person, active voice, concrete images,
no hashtags, 0-1 emoji (self-deprecating only)") is therefore the only written
source of the first-person requirement for fact-mode, although ADR-0044 is
superseded for fact-mode on every other point. A reader of ADR-0059 alone
cannot tell that first person is required.

A voice defect was confirmed in the fact-mode prompt text. The prompt's
reasoning steps used "the author" as the grammatical subject: the FACT step
carried the example `"the author notes this was for..."`, DESIGN INSIGHT asked
what "the author wants to build" and "values", and PERSONAL POSITION described
a preference "the author could reasonably carry forward". The only first-person
instruction was a style-constraint line at the end of the prompt, and nothing
checked the finished post against it. A post synthesized from those steps can
therefore refer to its own writer in the third person.

Constraints: Accepted ADRs are never edited, so ADR-0044 and ADR-0059 stay as
written. idea_fallback remains governed by ADR-0044 and is not touched. The
"nobody" / "the team" wording in ADR-0059's final evidence check concerns
unsupported capability-absence claims, a different concern from self-reference.

## Decision

1. **This record owns the first-person requirement for the published fact-mode
   post.** The published `post` is first person throughout; the person who did
   the work is "I"/"my", never "the author" or "the owner". The content of the
   requirement is the Voice bullet of ADR-0044, applied to fact-mode; this
   record does not change ADR-0044's governance of idea_fallback.

2. **DESIGN INSIGHT analyzes the work, not a person.** Its grammatical subject
   is the work, the pattern, the engineering choice, or the tension. It must
   still extract an engineering preference or design value, stated as something
   the final text expresses as the owner's first-person position, not as a
   standalone neutral claim such as "the work demonstrates...".

3. **PERSONAL POSITION is the explicit bridge.** It formulates the preference
   or value identified in DESIGN INSIGHT as a present-tense first-person
   position (I/my). It is deliberately not made neutral: that would lose the
   semantics that the final post carries an explicit personal position.

4. **The FACT step's attribution example is subject-neutral too.** The example
   attributes a stated reason to the commit ("that commit's own stated reason
   is...") instead of to "the author". The earlier belief that the FACT step
   needed no change was contradicted by the prompt text on disk.

5. **First person is a hard contract at synthesis, and voice is checked
   separately from evidence.** The instruction that synthesizes the post from
   the reasoning steps states the first-person contract. A separate FINAL VOICE
   CHECK sits beside the FINAL EVIDENCE CHECK; the two are different checks and
   are not merged.

6. **A deterministic, fact-mode-only gate rejects third-person self-reference
   in the synthesized `post`.** It is a distinct function from the shared
   post-content check, because that check also runs for idea_fallback. It
   matches the literal forms "the author", "the owner", "this author", "this
   owner" and their possessives, with the article in either case and the noun
   in lowercase only, so a capitalized component name is not a match. The set of
   forms is defined in code, not by any list in ADR-0044 (which defines none),
   and is extended only for a form actually observed in a real post. It is not a
   banned-word list and does not look at "nobody" or "the team".

Not decided here: the five-step contract, the final evidence check's scope,
idea_fallback, and the text of ADR-0044 or ADR-0059.

## Alternatives & Rationale

| Option | Rationale for outcome |
|---|---|
| Amend ADR-0059 or ADR-0044 | Rejected. Accepted ADRs are never edited; a changed decision is a new record. |
| Supersede ADR-0059 with a full restatement | Rejected. It would reopen the five-step reasoning contract, which this problem does not require. |
| Prompt-only fix, no output check | Rejected. The defect was that the instruction arrived late and was never checked against the actual output; a prompt change alone leaves that unchanged. |
| Make DESIGN INSIGHT and PERSONAL POSITION fully neutral | Rejected. The Owner requires the engineering preference to land as an explicit first-person position before the post is synthesized. |
| Extend the shared post-content check with the new rule | Rejected. That check runs for both modes, so the rule would change idea_fallback, which is out of scope. |
| A blanket banned-word list including "nobody" / "the team" | Rejected. Those words are legitimate in many posts, and their concern (unsupported capability-absence claims) belongs to the final evidence check. |
| Chosen: this record owns the requirement, subject-neutral reasoning with a first-person bridge, and a fact-mode-only literal self-reference gate | Fixes the stated source, the prompt structure and the missing output check without touching the earlier records. |

## Consequences

- `_build_fact_prompt()` carries the subject-neutral DESIGN INSIGHT, the
  first-person PERSONAL POSITION bridge, the first-person contract at
  synthesis, and a separate FINAL VOICE CHECK.
- `validate_structured_response()` rejects a fact-mode post containing a
  listed self-reference form, so the run fails before anything is published.
  A false positive (the literal words used in a non-self-referential sense, in
  lowercase) also fails the run for that day; this is the same failure
  semantics as the existing ADR-number and greeting checks.
- The gate checks only listed literal forms. It does not require "I" or "my" in
  the post and does not detect other third-person phrasing.
- The identity-context block of the prompt still labels its input as "author"
  state; it is input context, not instruction text for the post, and is not
  changed by this record.

## Confirmation & Revisit

Confirmed at unit level only: tests assert that posts containing the listed
forms are rejected, that first-person posts are accepted, and that wording such
as "the team", "nobody" and "the Author component" is not flagged. The real
effect is not yet confirmed: it requires a scheduled run that produces a post,
checked against the literal workflow log and the Registry record. Days with
only automated commits publish nothing and so cannot confirm it.

Revisit when a published post is found to refer to its writer in a form the gate
does not list, or when the gate rejects a post that does not refer to its
writer.

## Source

Owner follow-up instruction after a voice diagnosis of the fact-mode daily
LinkedIn post, 2026-10-08. The FACT step finding in Decision point 4 came from
reading the prompt text during implementation.
