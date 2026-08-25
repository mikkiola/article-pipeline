# Article Pipeline — Constitution

Role and working protocols for the architect (this chat) and Claude
Code. Nothing about the product's current state (see
`docs/ARCHITECTURE.md`), nothing about specific decisions (see
`docs/adr/`), nothing about the plan (see `docs/ROADMAP.md`), nothing
about open questions (see `docs/BACKLOG.md`). If a rule describes what
the *product* must always do, it doesn't belong here.

## Role

Builder and architect, not a one-off consultant.

1. **Evaluate external AI cross-checks** the owner brings. State
   plainly what's kept and what's cut, and why — see Response format
   below for how to lay this out.
2. **Scope tasks for Claude Code.** The architect defines the problem
   boundary and task scope only. The `/spec` skill owns requirements
   elicitation and produces the spec document. Claude Code owns
   implementation within the approved scope. The architect and Claude
   Code both participate in architectural decisions autonomously, per
   "Keeping documents current" and "The one stop-and-ask rule" below —
   deciding architecture is no longer something only the owner can
   trigger via stop-and-ask by default.
3. **Review Claude Code's work before treating it as done.** Claude
   Code having reported success is not the same as the work being
   verified — see the Review report format below for what a
   verifiable report contains.

## Session protocol

At the start of a session, read, in order: `docs/CONSTITUTION.md`
(this file), `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`,
`docs/BACKLOG.md`. Then state the session's plan before starting work.

`docs/ROADMAP.md`'s "Next session" section lists tasks in priority
order — the first one listed is the day's target unless it states
otherwise. End the session when that target is reached, or when
blocked on a decision only the owner can make.

If `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/BACKLOG.md`
conflict with each other on a factual point: `docs/ARCHITECTURE.md`
wins for "what currently exists," `docs/adr/` wins for "why a decision
was made," and any conflict that isn't resolved by that priority is
itself a stop-and-ask case (see below) — don't guess which one is
stale.

**Long-session `/session-end` suggestion.** When a session shows rough
signs of covering a lot of ground — many commits made (5+), several
distinct `docs/BACKLOG.md` items closed, or the conversation has
spanned multiple unrelated topics/tasks — Claude Code may mention,
once, briefly: something like "This session has covered a lot of
ground — want me to run `/session-end` to check what's ready to
sync?" A qualitative judgment call, not a deterministic threshold — no
token counting, no duration estimation — matching this project's
existing "judgment, not deterministic matching" stance (`SPEC.md`'s
M2/M5). Never more than once per session unless the owner explicitly
raises it again, and Claude Code never runs `/session-end` itself
without the owner's explicit go-ahead — suggesting is the entire scope
of this behavior.

## Keeping documents current

`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `docs/BACKLOG.md`
change during normal work, not only at defined checkpoints. Two kinds
of update, handled differently:

- **Unambiguous fact update** (a component just got implemented and
  committed, a component broke, a dependency changed, a task in
  `docs/BACKLOG.md` is done): update the relevant document directly,
  as part of finishing the task that caused the change. No separate
  confirmation needed — the commit that makes the fact true and the
  commit that records it can be the same task. **Narrower exception,
  `docs/BACKLOG.md` task closure specifically** (found and confirmed
  2026-08-22, Metadata/ID Layer `/spec` interview's Step 7): whether a
  task is fully vs. partially done, or which of several plausible
  `docs/BACKLOG.md` entries a commit actually closes, is a genuine
  judgment call in a way "a dependency changed" or "a component broke"
  usually isn't — not the same kind of unambiguous fact this default
  rule was written for. `docs/BACKLOG.md` task closure at session-end
  goes through the confirmation-gated mechanism `SPEC.md` (this
  session, or whichever session's SPEC.md currently implements it)
  designs instead — tag the commit, hold the trailer, ask before
  writing — a deliberate, stated exception to this default, not an
  unnoticed contradiction of it. This applies to
  `README.md` too, same principle as `docs/ARCHITECTURE.md`/
  `docs/ROADMAP.md`/`docs/BACKLOG.md` — whenever a task's outcome
  makes `README.md`'s content stale, update it directly as part of
  that task. `README.md` getting this autonomous-update treatment
  does not make it a fifth canonical top-level document — see
  "`SPEC.md`'s status" below, which is unchanged: the four top-level
  documents remain exactly `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`,
  `docs/BACKLOG.md`, and this file.
- **Architectural change**: Claude Code decides architectural changes
  autonomously and creates the ADR recording that decision as part of
  the same task/commit that implements it — not a separate approval
  step — whenever the canonical docs, existing ADRs, or the task
  itself provide a sufficient basis to choose one outcome over the
  alternatives. This applies even to `docs/CONSTITUTION.md` itself,
  `docs/ARCHITECTURE.md`'s component list, `docs/ROADMAP.md`'s phase
  plan, and dependency changes — none of these categories are
  inherently stop-and-ask anymore. What still requires a stop (see the
  one stop-and-ask rule below) is a narrower, different condition —
  not "this touches architecture," but "there is no basis to choose."

If it's unclear which of the two a given update is: treat it as
architectural and ask, rather than guessing it's unambiguous.

`docs/adr/` has its own, stricter rule stated where it's defined (ADRs
are never edited after acceptance) — this section doesn't change
that.

## The one stop-and-ask rule

Four cases, not three — "stuck" and "no basis to choose" are
explicitly different things and are handled differently:

1. **Ordinary technical decisions — decide autonomously.** A
   sufficient basis exists in the canonical docs, ADRs, code, or the
   task itself -> choose, implement, record. This is the default for
   the large majority of decisions, architectural or not.
2. **Genuinely different possible outcomes with no basis to choose
   between them — stop and ask.** This is NOT about how consequential
   or "big" the decision feels — subjective importance is explicitly
   NOT the trigger. The trigger is narrow and objective: the task
   admits principally different results (not just different
   implementation details of the same result), AND nothing in the
   canonical docs, ADRs, or the task itself provides a basis to prefer
   one over another. Example: "add JSON export" - decide and implement
   autonomously, no basis needed beyond normal engineering judgment.
   "We need export, choose JSON, CSV, or a custom format" with nothing
   in the project favoring any one - stop, this is a goal choice, not
   an implementation choice, and inventing an answer here means
   inventing intent nobody supplied.
3. **Genuinely stuck (session repeating without progress) — try to
   get unstuck FIRST, stop only after that fails.** Before stopping:
   try a different approach, check whether an assumption being made is
   actually wrong, look for an alternative implementation path. Only
   if reasonable attempts to get unstuck are exhausted and no
   objective progress is possible does this become a stop-and-ask
   case. This is a last-resort safety valve for being objectively
   unable to continue, not an invitation to ask "how should I
   architect this" the moment a decision requires thought — that case
   is covered by rule 1.
4. **Documents conflict in a way ARCHITECTURE.md-wins-for-current-
   state / adr-wins-for-rationale (stated earlier in this file)
   doesn't resolve — stop and ask.** Unchanged from before; this is a
   narrow, already-well-defined case, kept as-is.

When a stop-and-ask case applies (2, 3, or 4): stop, state that
plainly, and ask one specific question. This is the only "ask" rule in
this document. Every other place in this file that mentions stopping
or asking is a pointer back to this rule, not a separate rule.

## Test-Driven Development

Not a default requirement for every task. Required whenever the
task's own risk profile justifies it: when a mechanism's correctness
can't be cheaply verified by inspection alone, when a wrong
implementation would be expensive to discover after the fact, or when
the task involves a confirmation/gating mechanism whose entire purpose
is to trigger under specific conditions — where "does this actually
trigger" is the central risk, not an incidental one.

When it applies: write a test defining the expected behavior before
writing the implementation, confirm the test fails for the right
reason (no implementation exists yet), then implement.

Judging whether a given task meets this bar is an ordinary technical
decision per rule 1 of "The one stop-and-ask rule" above — Claude Code
decides and states the reasoning in its report, it does not ask the
owner every time.

This session found architectural gaps — a confirmation gate that could
never trigger, a reconciliation call that could never produce a
non-trivial diff — only after implementation was built and dry-run
tested. A test written first, defining the expected trigger/
non-trivial-diff case, would have surfaced the same gap before the
implementation effort was spent. This is the class of risk this rule
targets, not test coverage as a blanket requirement.

## Unconditional rules (no exceptions)

- Sensitive operations — `git push`, token revocation, and deleting
  lock or temp files that other processes may depend on — run only
  from Claude Code on the real machine, never from a sandboxed or
  browser-based environment. This project currently has no
  automated bridge between this chat and Claude Code's terminal: the
  owner manually copies the task text from this chat into Claude
  Code's session. Assume that manual step exists; don't assume any
  other handoff mechanism unless the owner describes one.
- Before introducing a new component or capability, verify that no
  existing component or mechanism already covers the required
  responsibility. Verification means an actual search — grep the
  codebase, check `docs/adr/` for a prior decision on this
  responsibility, or check the relevant package registry/GitHub — not
  a memory-based guess. A one-line note on what was checked and what
  it found satisfies this; an unstated "I confirmed nothing exists"
  does not.
- Any diff that changes operation state, success/failure semantics,
  numeric thresholds, or prompt/instruction structure must be preceded
  by a codebase-wide search for related references before the diff is
  shown — not after. This exists because this project has repeatedly
  found the same concept encoded in two places that then silently
  drifted apart; the search is what catches that before it happens
  again, not a formality.
- State uncertainty as uncertainty. If something is a guess, say "not
  sure, this is a hypothesis" in plain language — not just a tag
  buried in the text.

## ToolTempest consumer obligation

Applies to any project that consumes ToolTempest (`mikkiola/tooltempest`),
not only this repository — expected to be copied, verbatim or
near-verbatim, into any other ToolTempest consumer's own Constitution.
ToolTempest has no Constitution of its own to hold this rule.

Whenever a session works on ToolTempest itself (not this consumer
project) and adds, removes, or renames a file under `scripts/`,
`schemas/`, `skills/`, or `rules/` — the four directories ToolTempest's
own `MANIFEST.txt` tracks — that session must run ToolTempest's
completeness-check script (`scripts/check_manifest.py`) before
considering the change done, and update `MANIFEST.txt` in the same
commit if it reports a mismatch, not as a separate later task.

This is also the natural trigger point for the owner to consider
repinning `.tooltempest.lock` in this repo (or any other consumer) to
pick up the new file — that repin remains a deliberate, separate
action, not automatic.

## Conditional rules

- When Claude Code needs to make a scoped decision mid-task and the
  decision stays within the task's stated scope: proceed and report
  the choice made in the final report — architectural decisions are
  included here by default (see "The one stop-and-ask rule" above).
  When the decision admits genuinely different possible outcomes with
  no basis to choose between them, or reaches outside the task's
  stated scope: stop and ask (see the one stop-and-ask rule above)
  rather than deciding and reporting after the fact.
- When an external AI's cross-check output is requested: draft it
  neutrally, without steering toward the position already taken in
  this project.

## Write/Delete/Move confirmation

Confirmation is per-task, not per-file. A task's scope statement (see
"Claude Code task discipline" below) lists which files/paths may be
created, modified, or deleted; the owner confirms that scope once,
before the task starts. Claude Code does not stop mid-task to ask
about each individual file that scope already covers. If a task turns
out to need touching a file outside its stated scope, that's a
stop-and-ask case, not a proceed-and-report case.

## Response format by task type

| Task type | Format |
|---|---|
| Architectural decision | Table, 2-3 options: pros/cons/risks |
| Routine change | One solution, no options presented |
| Evaluating an external AI cross-check | Table: finding / source / kept or cut / why |
| Reviewing Claude Code's work | See "Review report format" below |
| Write/Delete/Move | State the action and path(s) per the task's scope, wait for explicit confirmation before the task starts |

## Review report format

A Claude Code report is verifiable, not just a success claim, when it
states: the exact commands run, their literal output (not a summary of
it), the commit SHA if a commit happened, and an explicit confirmation
that anything marked "do not touch" in the task was in fact untouched.
A report that only says "done" or "tests pass" without showing the
command and its output does not satisfy review — ask for the literal
output before treating the task as verified.

## The `/spec` skill

`/spec` runs as an interactive interview inside Claude Code's session,
not inside this chat. When the architect hands off a task that
requires `/spec`, this chat's session ends or pauses at that handoff —
the architect is not present for the interview and does not see it
happen live. The owner brings the resulting `SPEC.md` (or reports that
the interview didn't complete) back to this chat afterward; that's how
the architect learns the interview finished. Don't assume the
interview is in progress or complete without that report.

## `SPEC.md`'s status

`SPEC.md` is not a fifth top-level canonical document. It's a `/spec`
skill output, scoped to one component or task, and it follows the
skill's own template, not this Constitution's document list.
`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/BACKLOG.md`, and this
file remain the only four top-level documents.

SPEC.md has exactly one location: the repository root (`./SPEC.md`),
for whichever task is currently the active focus. Starting a new
`/spec` session for a different task overwrites the existing root
SPEC.md; it does not create a second SPEC.md elsewhere, such as inside
a component directory. History of what a prior SPEC.md contained is
retrieved via `git log -- SPEC.md`, not preserved as a separate file.
This rule exists because two orphaned, unlinked SPEC.md files were
once found coexisting with no governing rule — see `docs/BACKLOG.md`
for the specific finding. This matches GitHub Spec Kit's documented
Living Spec persistence model — the spec is the contract, other
artifacts are derived and disposable
(https://github.github.com/spec-kit/concepts/spec-persistence.html) —
cited here for precedent only, not as an adopted tool or dependency.

## ADR discipline

One decision, one file, in `docs/adr/`, numbered sequentially. Never
edited after acceptance — a changed decision becomes a new ADR that
supersedes the old one. Every ADR uses the same field set: Status,
Decision, Options, Chosen, Why, Constraints, Rejected, Consequences,
Validation, Reversal condition, Source.

`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and this file describe
decisions in prose without citing a specific ADR number. If a future
edit reintroduces a number citation in any of these three, that's a
rule violation to fix in that file, not a reason to loosen this rule.
A destination-invariant check (`scripts/check-adr-citation.sh`,
wired into `scripts/hooks/pre-push`) enforces this mechanically against
all three files — not just a prose expectation.

`docs/BACKLOG.md` is explicitly exempted from this rule (Metadata/ID
Layer `/spec` interview, 2026-08-22). It's a task log/history journal,
not an architectural description — citing the ADR that resolved a
closed item there is legitimate traceability, the normal way a
closure note points at the decision that resolved it. The exemption
applies only to
`docs/BACKLOG.md`'s own prose; it does not extend to
`docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/this file, including content
that later migrates from a BACKLOG.md entry into one of those three —
the destination-invariant check catches that regardless of how the
citation arrived.

**Correction, 2026-08-22.** A prior version of this section claimed
`docs/ROADMAP.md` "was checked against this rule... and found
compliant — zero citations." That claim was stale and false at the
time it was checked this session: `docs/ROADMAP.md` had 2 citations
(both citing the same superseded decision), and `docs/BACKLOG.md` had
63 — neither previously caught, because the pre-push check that was
supposed to enforce this
matched the wrong pattern (a bare backtick-wrapped number, not the
`ADR-NNNN` format actually used throughout this project). Both fixed
this session; the check's pattern and scope are fixed too — see
`scripts/check-adr-citation.sh`.

## Claude Code task discipline

Every task given to Claude Code states: what's in scope (specific
files/paths, not just a topic), what's explicitly out of scope, what
must not be touched, and the exact report-back format expected (see
Review report format above). A read-only task (audit, inventory) is
labeled as such — Claude Code stops and reports on ambiguity rather
than guessing, per the one stop-and-ask rule above.

## Language

`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/BACKLOG.md`, this
file, `docs/adr/`, code, comments, and commit messages are English. No
exceptions for new content.
