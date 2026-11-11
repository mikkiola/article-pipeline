---
id: ADR-0074
status: Accepted
supersedes: null
superseded_by: null
source_type: inferred
---

# ADR-0074: The Constitution Holds Project Rules Only; Universal Rules Come from the Pinned ToolTempest File

## Status

Accepted by the Owner, 2026-11-10. It supersedes no ADR.

## Context & Constraints

Observation at commit `feae5c0`: `git show feae5c0:docs/CONSTITUTION.md | wc -l` prints 534. Most of those lines state rules that are not specific to this repository: the reading order, the mission card, commit trailers, the stop-and-ask rule, the review report, the ADR rules, and the language rule. The same rules appear in the Constitutions of the other consumers in different words (`git show 896e911:docs/CONSTITUTION.md` in `brain`, `git show 7e66e19:docs/CONSTITUTION.md` in `radar`).

ToolTempest states the universal rules once, in `docs/tooltempest/universal-rules.md`, and delivers that file through the contract root that its materializer installs (ToolTempest ADR-0020). The Owner approved the direction and this amendment on 2026-11-10.

## Decision

1. The Constitution holds the working rules of this repository only. For every universal rule it points to the universal rules and repeats no obligation from them.
2. The universal rules are binding here. A document that contradicts them is fixed.
3. The universal rules reach this repository through the ToolTempest pin. This change does not alter the pin. The consumer change is pushed together with the repin, after the ToolTempest push, subject to the Owner's separate permission under WR-14.
4. The entry points route to the universal rules and to the Constitution.
5. The Constitution carries no dated notes. Git history and the decision records hold the history.

## Alternatives & Rationale

- Keep the universal rules in the Constitution: rejected, because the consumers' copies differ (Context) and nothing compares them.
- Track a copy of the universal rules here: rejected, because a tracked copy is a second source that the pin does not control.

## Consequences

- Until the repin, the universal rules file is absent here and the pointers to it have no target. A fresh clone has it only after the repin and the setup in `README.md`.
- The `Syncs:` trailer and the capability-or-runtime classification stay project rules.
- The section "Write/Delete/Move confirmation" and the write row of the response-format table are deleted (`git show feae5c0:docs/CONSTITUTION.md | sed -n 361,369p`; `git show feae5c0:docs/CONSTITUTION.md | grep -n "Write/Delete/Move |"`). Universal rule WR-13 replaces them, as the Owner decided on 2026-11-10: the task prompt is the approval, and `[ЗАПРОС]` stays for token revocation, deleting a file another process may depend on, and an edit of a Constitution. The earlier text approved a task's scope once before the task and stopped for a file outside it; WR-13 keeps that and adds the explicit cases.
- Other deleted text: the end-of-session clause of the session target, which contradicts WR-5 (`git show feae5c0:docs/CONSTITUTION.md | sed -n 43,45p`); the response-format rows for an architectural decision, a review, and a write (`git show feae5c0:docs/CONSTITUTION.md | sed -n 371,379p`), which WR-3, RV-1, and WR-13 cover; the pointer to the Cowork-layer decision by file path, which DR-11 forbids in a Constitution (`git show feae5c0:docs/CONSTITUTION.md | grep -n "0042"`); the dated notes (`git show feae5c0:docs/CONSTITUTION.md | grep -n -i "dated note\|Owner-directed 2026"` prints lines 315 and 327; the other dated passages are in the ranges below); the skills-directory location in the Cowork boundary (`git show feae5c0:docs/CONSTITUTION.md | grep -n "claude/skills"`).
- Text of the earlier Constitution that is not carried over (explanation, history, rationale, examples, precedents; the closed set of top-level documents of base lines 131-135 and 402-409 is carried as AP-14): `git show feae5c0:docs/CONSTITUTION.md | sed -n '43,45p;79,81p;110,113p;116,117p;131,135p;136,146p;157,161p;170,172p;176,181p;192,205p;244,246p;268,274p;297,300p;327,345p;402,423p;433,435p;445,455p;457,467p;487,504p;525,534p'`. The whole removed text is `git diff feae5c0 -- docs/CONSTITUTION.md` (lines that start with a minus).
- The mechanical-verification section was prose without rule IDs (`git show feae5c0:docs/CONSTITUTION.md | grep -c "AP-"` prints 0). The Constitution now holds it as the rows AP-12 and AP-13.
- Owner decisions of 2026-11-11. Commit and push: a local commit needs no Owner confirmation (the agent checks the full diff and runs the prescribed checks first); any `git push` needs a separate explicit permission under universal rule WR-14. `/session-end` therefore makes a local commit and does not push: the skill is repository text (`git ls-files .claude/skills` lists it; ToolTempest's `MANIFEST.txt` does not name it), so it is fixed here. Repin: a task prompt that names a repin authorizes the change of `.tooltempest.lock` and its local commit under the conditions of the consumer contract.
- The rule sentences of `CLAUDE.md` that universal rules state are deleted there (session-end as an Owner action: WR-5; permission to prepare separate from permission to commit or push: WR-13 and WR-14; consumer pin updates are explicit steps: the consumer contract; the product and private-runtime boundary: AP-9 to AP-11), and those specific to this repository moved to the Constitution as AP-15 and AP-16 with a pointer left; the base text is `git show feae5c0:CLAUDE.md`. One sentence stays in `CLAUDE.md` until the repin delivers WR-14: a `git push` needs the Owner's separate explicit permission. It keeps the push restriction of the base text in force while the universal rule is absent, and it is a known conflict with the rule that an entry point holds no rule. The sentence "This offline phase changes no settings, permissions, hooks, MCP activation or private runtime state" is deleted: it described the phase of the instruction-edit task, not a standing rule. The two "Work areas" architecture bullets are replaced by a pointer to `docs/ARCHITECTURE.md`, which holds the components.
- The live references to removed Constitution text are fixed: `.claude/skills/session-end/SKILL.md` now cites the universal "Reading order", and `SPEC.md` cites WR-6. The historical references (`CURRENT_MISSION.md`, the history of `docs/BACKLOG.md`, comments in code and tests, and Accepted ADRs, which are immutable) stay open items, because rewriting them would rewrite mission and backlog history. They are listed with their file and line in the message of the commit that adds this record, because DR-9 puts a snapshot there.

## Confirmation & Revisit

The commit that adds this record carries the checks it ran and their output in its message.

The RV-6 ledger of this change, one row per obligation of the earlier Constitution (CARRIED, DELETED, or NA), is kept with the change report outside the repository. Rows of it that the Constitution does not restore are explanation, examples, or provenance (TX-6), with two exceptions: the "no ADR needed" exception for the commit-message convention (base lines 202-205) was removed because "How a rule changes" requires an ADR for a change of a Constitution, and the pointer to the backlog (base lines 176-177) is a pointer, not a rule, and base lines 178-181 are the narrative of a 2026-09-16 incident, which is history (TX-6). The commands in Consequences print their base text, in particular base lines 79-81, 110-146, 157-161, 170-172, 244-246, 327-345, and 433-435. The staged text prevails over the ledger.

Revisit when a rule that this repository needs cannot be stated as a project rule without contradicting a universal rule.

## Source

The Owner's task of 2026-11-10 and the Owner's decisions of 2026-11-11, executed in Claude Code sessions. This record is unpushed, and the Owner instructed that it is editable. Claude Code drafted the wording, so `source_type` is `inferred`. No external AI cross-check was made.
