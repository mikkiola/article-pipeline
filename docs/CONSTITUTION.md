# Article Pipeline — Constitution

| Field | Value |
|---|---|
| Type | Reference |
| Holds | The working rules of this repository only |
| Universal rules | [`docs/tooltempest/universal-rules.md`](tooltempest/universal-rules.md), section "How every repository works" |

The universal rules are binding here. They state the reading order, which file
wins on a conflict, how a rule changes, the function of each document, the write scope
(WR-13), and the ADR, commit, review, mission, and language rules. This file does not repeat
them. MUST, SHOULD, and MAY have the meaning defined there.

After the repin that delivers it, the universal rules file is installed from
the commit pinned in `.tooltempest.lock` and is not tracked. In a fresh clone, run "Setup of a fresh
clone" in `README.md` first.

## Role

Builder and architect, not a one-off consultant.

| Party | Role |
|---|---|
| Architect (the claude.ai chat) | Defines the problem boundary and the task scope only. Evaluates external AI cross-checks. Reviews Claude Code's work before it counts as done. |
| `/spec` skill | Elicits requirements and produces `SPEC.md`. |
| Claude Code | Implements within the approved scope. |

## Session

| ID | Rule |
|---|---|
| AP-1 | The session target is the `docs/ROADMAP.md` current pointer. The universal conflict table names the exception. |
| AP-2 | When a session covers a lot of ground (signs: five or more commits, several closed BACKLOG entries, several unrelated topics), Claude Code MAY say once, briefly, that `/session-end` is available. This is a judgment, not a threshold: no token counting, no duration estimation. Do not repeat it unless the Owner raises it. Claude Code MUST NOT run `/session-end` without the Owner's go-ahead; the suggestion is the whole behavior. |
| AP-3 | No automated bridge exists between the architect chat and Claude Code. The Owner copies the task text by hand. Assume no other handoff unless the Owner describes one. |
| AP-4 | `/spec` runs as an interactive interview inside Claude Code, not in the architect chat. The chat ends or pauses at the handoff, and the architect does not see the interview. The architect learns the result only when the Owner brings `SPEC.md` back or reports that the interview did not complete. Do not assume the interview is in progress or complete without that report. |

## Documents

| ID | Rule |
|---|---|
| AP-5 | When you cannot tell whether an update is a plain fact update or an architectural change, treat it as architectural and ask. |
| AP-6 | A commit that changes a fact in `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, or `README.md` MUST carry `Syncs: <path>`, one trailer line per file. `/session-end` reads these trailers. |
| AP-7 | An ADR starts with YAML frontmatter (DR-7). An ADR MAY add a section that its decision needs. |

## Decisions

| ID | Rule |
|---|---|
| AP-8 | When a session repeats without progress, first try another approach, test your assumptions, and look for another implementation path. Stop and ask only when attempts are exhausted and no objective progress is possible. This is a last resort; WR-1 and WR-2 cover architecture questions. |

## Project rules

| ID | Rule |
|---|---|
| AP-9 | Before you create a script, workflow, directory, or integration, classify it as a Reusable Product Capability or as Customer/Personal Runtime. State the class and the reason in the report. |
| AP-10 | A Reusable Product Capability is generic, is configured only through environment variables or parameters, and is safe to publish. |
| AP-11 | Customer/Personal Runtime is anything specific to one installation: accounts, folder or deployment identifiers, credentials, chat settings, schedules, account-specific orchestration, personal glue scripts. You MUST NOT create it in this repository, including in hidden or ignored directories. It lives in a private location outside this repository. |
| AP-14 | The top-level documents are `docs/CONSTITUTION.md`, `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/BACKLOG.md`. `SPEC.md` and `README.md` are not part of that set. |
| AP-15 | Neighboring repositories are separate systems. Consume established data contracts. Do not read their private checkouts or add implicit integrations. Access another repository only within the current task's explicit allowlist. |
| AP-16 | Draft acceptance, permission to publish, and a confirmed external publication are distinct outcomes. Component test commands are not permission to run production entry points and are not a claim that an instruction edit ran them. Inspect the selected test module and its doubles before you run it. For an instruction-only change, check links, rule scopes, the exact diff, and `git diff --check`; do not run the daily publishing or authoring entry points, dispatch workflows, or exercise external services to validate it. Reuse `/session-end` and the installed shared skills; do not copy their procedures into project agents or additional skills. Preserve existing work. |

## Response format

| Task type | Format |
|---|---|
| Routine change | One solution. No options. |
| Evaluation of an external AI cross-check | Table: finding, source, kept or cut, reason. |

## ADR discipline

The universal rules state the ADR rules. This repository enforces two of them
mechanically.

| Rule | Check | Runs in |
|---|---|---|
| No ADR number in `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, or this file | `scripts/check-adr-citation.sh` | `scripts/hooks/pre-push` |
| Unique ADR numbers; the header number equals the file-name number | `scripts/check_adr_numbering.py` | CI |

`scripts/generate_adr_index.py` generates `docs/adr/ADR-INDEX.md`.

## Mechanical verification scope

| ID | Rule |
|---|---|
| AP-12 | A rule gets a script check (in `scripts/verify.py`, `scripts/check-adr-citation.sh`, or an equivalent) only when it is a document-format convention that a script verifies cheaply and deterministically: headings, stable IDs, citation patterns, required fields. |
| AP-13 | A judgment-based, behavioral, or process rule MUST NOT get a script check, even where tooling would allow it: a script would present a human or agent decision as a deterministic fact. |

## Cowork-layer practice boundary

`obsidian-notes`, `content-social`, `human-text`, `docops-swagger`,
`ods-ecosystem`, and `incident-escalation` are practices of the Owner's Cowork
layer. None exists as a skill file in this repository or in ToolTempest. The source of
truth for them is the Cowork layer's own instructions. This
repository does not hold, version, track, or govern them. The decision record
`cowork-layer-practice-boundary` states the grounds to revisit this boundary.

## Language

Named exception to the universal language rule: the Telegram HITL bot's
Owner-facing text is Russian. It covers Owner Verdict prompts, Change Proposal
approval and rejection messages, Weekly reports, and `SYSTEM_FAILURE` and
`SAFETY_PAUSE` alerts.

## ToolTempest consumer obligation

[`docs/tooltempest/consumer-contract.md`](tooltempest/consumer-contract.md)
states the obligation. It is installed from the pinned ToolTempest commit and is not tracked.
