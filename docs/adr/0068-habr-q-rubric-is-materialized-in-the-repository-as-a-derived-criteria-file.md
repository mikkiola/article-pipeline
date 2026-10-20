---
id: ADR-0068
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0068: The Habr Q check's rubric is a criteria file inside this repository, derived from the `human-text` practice

## Status

Accepted on 2026-10-15 as a decision. Not yet confirmed by a real run. Does not
supersede or amend ADR-0042 (see Consequences).

## Context & Constraints

The Q check of the Habr draft path (ADR-0071, `SPEC.md` M9 requirement 44)
assesses a draft against the infostyle criteria of the owner's `human-text`
practice. Two facts bound the choice:

- The practice exists as a conversational skill prompt outside this repository
  (under the owner's `~/.claude/skills/synced/`). It is not a callable
  function, it yields no score, and it is not present in the unattended
  runtime, which checks out only repositories.
- The owner confirmed (2026-10-15) that the paid Glavred API is not integrated
  at this stage and that no separate quality engine is built.

A Q check inside an unattended workflow therefore needs the criteria in a place
the workflow can read.

## Decision

The criteria are carried as `habr_draft/rubric_infostyle.md`, a short file used
as the rubric block of the Q judge's prompt. It lists the criteria by id
(facts instead of evaluations, one thought per sentence, officialese, markers of
AI-generated text, ambiguity, claims without evidence), the severity scale and
an integer score from 0 to 100. The score is a judgment against this rubric only,
is not presented as an objectively proven metric and says nothing about whether a
text may be published. The file's hash is recorded in every run record.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Read the skill from the owner's home directory at run time | Not chosen. Not available in the runtime; ties production behavior to one machine. |
| B. Integrate the paid Glavred API | Not chosen. Owner decision 2026-10-15: not at this stage. |
| C. Build a general scoring engine | Not chosen. `SPEC.md` requirement 52 forbids an abstraction beyond this one path. |
| D. Chosen: a derived criteria file used as a prompt rubric | Smallest reuse that works unattended; versioned and hashed with the code. |

## Consequences

- The rubric can drift from the skill it was derived from. It is a copy of
  criteria, not a synchronized one; changing the skill does not change the
  check, and the recorded hash shows which rubric a run used.
- ADR-0042 records that the six practices have no file in this repository and
  names, as its revisit condition, materialization of one of them as a
  `SKILL.md` or equivalent artifact. This record does not decide whether a derived
  criteria file for one check meets that condition; it makes no change to
  ADR-0042 or to `docs/CONSTITUTION.md`. If the owner judges that it does, the
  superseding record is a separate action.
- Q has no pass or fail without the owner's threshold (ADR-0071 point 6).

## Confirmation & Revisit

Not confirmed. Confirmation requires a calibration run (an owner-approved paid
call) that records a Q score for the owner's reference text and for a draft.

Revisit when the threshold is calibrated, or if the owner replaces the Q check
with an external service.

**Source.** Owner decisions of 2026-10-15 (no Glavred API; reuse before building;
minimal MVP); reading of the `human-text` skill file the same day. No external AI
contributed to the decision.
