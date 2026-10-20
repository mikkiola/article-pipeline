---
id: ADR-0071
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0071: The Habr draft acceptance contract is separate from R6 and is never publication approval

## Status

Accepted on 2026-10-15 as a decision. Not yet confirmed by a real run: see
Confirmation & Revisit. Does not supersede or amend ADR-0044, ADR-0046, ADR-0047,
ADR-0042 or ADR-0052. Drafted as ADR-0067 and renumbered to ADR-0071 on
2026-10-16, before its first commit, because ADR-0067 was taken on `main` by the
LinkedIn run-outcome ADR.

## Context & Constraints

`SPEC.md` M8 defines R6 (a publication needs at least one Claim that meets five
conditions jointly, including `evidence.scope = external`) and three outcomes for
the Quality Gate, with `SYSTEM_FAILURE` including "Linkup unavailable". M8 is not
built (`quality_gate/` holds only a placeholder) and is blocked on Path B Claim
Extraction. `docs/ROADMAP.md` separately records a committed Habr content
requirement: at least one code/artifact fragment and at least one externally
sourced enrichment per article.

Habr Draft Automation needs an acceptance contract now, for a path that produces a
draft for the owner, not a publication. Four facts bound the answer:

- The only automated check that exists for a Habr draft today is
  `strategy_layer/language_check.py`'s `looks_russian`.
- Linkup is a retrieval mechanism (`retrieval_source`), not evidence and not a
  verifier (`SPEC.md` FR38). `evidence_package/driver.py` runs the search phase
  only; assigning a status and source to a result is an interactive step.
- Habr's own rules (`habr.com/docs/help/rules`, last edited 2026-07-08, read
  2026-10-15) contain requirements that are machine-checkable in part (rule 3,
  typography and formatting), requirements that are editorial judgments
  (rule 1, self-promotion; rule 2, subject and format), and rule 4, which
  prohibits publishing generated material. No automated check can establish
  compliance with rule 4.
- The language of the text, and the presence of a code fragment, are this
  project's own requirements, not Habr's.

ADR-0044 defines L2 as a public repository link gated on a live `gh repo view`
check. That definition is not changed here.

## Decision

**1. A separate contract, scoped to Habr Draft Automation.** R6 and M8's three
outcomes are not applied to this path and are not modified. The LinkedIn path's
contract is untouched. `SPEC.md` carries the Habr contract in its own section and
adds one scoping note to M8 so the two cannot be read as one.

**2. Three layers, never collapsed into one check or one outcome.**

- (a) *Habr platform rules* — only the parts that can be checked objectively
  from the rules' own text.
- (b) *Project acceptance requirements* — Russian-language output, at least one
  evidence-backed code/artifact fragment, and other owner-confirmed content
  requirements. These are the project's bar and are never presented as Habr's
  rules.
- (c) *Human review* — authorship character, compliance with rule 4, and
  suitability for publication. Not automated and not decided by any check.

**3. Success of an internal run requires all mandatory automated checks:** L1
(fact verification), (a), (b), and Q (quality, infostyle). The outcome
`INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW` means only that these four passed. It is
never publication approval, and the run's saved report states so. A draft is not
represented as publication-ready for Habr unless the owner has independently
created or substantially authored the final article, with generated material
limited to what the current Habr rules permit.

**4. Outcome vocabulary.**

- `QUALITY_BLOCK` — a per-attempt verdict: an executed mandatory check found a
  content or quality failure. It triggers correction and a full re-check.
- `BLOCKED` — the terminal state when two correction cycles after the initial
  draft have not produced a pass on all mandatory checks.
- `SYSTEM_FAILURE` — a mandatory check could not be executed (crash, missing
  input, dependency outage). It is reported separately, is never converted to
  `QUALITY_BLOCK` or `BLOCKED`, and does not consume a correction cycle.
- A failed or unavailable optional Linkup enrichment triggers none of these. It
  is recorded as skipped enrichment.

**5. Not automated, by decision.** Whether a draft crosses from an engineering
case study into self-promotion (rule 1), and authorship character (rule 4), are
owner review. "Must differ from the LinkedIn post" is not a rule and not a check;
it may appear only as an optional editorial note.

**6. Open calibration item.** The numeric Q-acceptance threshold is not set. It
requires owner calibration against real examples. The check mechanism may be
planned and built before it; production acceptance is not declared validated
before it.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Apply R6 to Habr as written | Not chosen. R6 needs Path B Claim Extraction, which is not specified or built, and an external verified claim as a hard gate. That would make the Habr path unbuildable for an unrelated dependency. It would also couple a draft-for-owner path to the publish gate. |
| B. One combined "H" check covering Habr rules, project requirements and review | Not chosen. It presents the project's own bar (language, fragment) as Habr's rules, and implies that automation can establish rule 4 and rule 1 compliance, which it cannot. |
| C. Treat a Linkup outage as `SYSTEM_FAILURE`, as M8 does | Not chosen for this path. Linkup is optional enrichment here; an outage of an optional input must not stop a run whose mandatory checks can execute. |
| D. Make `QUALITY_BLOCK` terminal on first failure | Not chosen. Correction is the point of the bounded loop; a first-attempt content failure is expected, and ending there would discard the revision mechanism. |
| E. Unbounded revision until pass | Not chosen. Unbounded cost and no guarantee of convergence; the bound is 2 correction cycles. |
| F. Chosen — a separate, scoped contract with three explicit layers and a bounded loop | Keeps the LinkedIn contract and M8 intact, keeps each requirement attributed to its real source, and keeps human judgments out of automated outcomes. |

## Consequences

- `SPEC.md` gains a Habr Draft Automation section, a scoping note on M8, a
  milestone and open items. M8's text on R6 is not edited.
- `docs/ROADMAP.md` still lists "at least one externally-sourced enrichment per
  article" as committed. After this decision that enrichment is optional for
  acceptance on the Habr path. ROADMAP is not edited by this record; reconciling
  it is a separate documentation task.
- Q has no pass or fail without a threshold. A run with an unset threshold ends as
  `SYSTEM_FAILURE` (a mandatory check that cannot execute): the owner stated this
  treatment on 2026-10-15 (`SPEC.md`, open questions). Until a threshold is set, no
  run can reach `INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW`.
- Every run report states that the outcome is not publication approval.
- The Habr contract adds no new field to `PublicationRecord`. A draft that has not
  been published has no `url` or `published_at`, so it is not represented there.

## Confirmation & Revisit

Not confirmed. Code that implements this contract exists in `habr_draft/`
(written 2026-10-15, model and GitHub calls mocked in its tests), but no real run
has happened. Confirmation requires a real run
whose saved report shows each of L1, (a), (b) and Q executed, and the outcome
recorded as defined above.

Revisit if Habr's rules change in a way that moves a machine-checkable requirement
into editorial judgment or the reverse; if Path B Claim Extraction is built and
the owner wants R6 applied to Habr; or when the Q threshold is calibrated.

**Source.** Owner decisions confirmed in the pre-spec and spec session of
2026-10-15; Habr's rules page read the same day (page text obtained through a
fetch tool, so exact wording is to be re-read from the page at plan time). No
external AI contributed to the decision.
