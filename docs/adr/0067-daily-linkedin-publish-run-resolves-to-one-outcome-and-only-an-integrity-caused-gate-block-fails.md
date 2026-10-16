---
id: ADR-0067
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0067: Every daily LinkedIn publish run resolves to one outcome, and only a gate block caused by an integrity violation fails the run

## Status

Accepted on 2026-10-15 as a decision. The product change is implemented and tested
locally and is not yet confirmed by a real scheduled run: see Confirmation &
Revisit, which is open. Does not supersede or amend ADR-0054, ADR-0056 or ADR-0064.

## Context & Constraints

State read on 2026-10-15:

- Before this decision, `linkedin_publisher/daily_publish.py` had four early
  returns (SAFETY_PAUSE open, an existing `pass` record, a bootstrap-gate block, an
  automation-only day) and all of them, like a normal publish, ended with exit
  status 0. A run that blocked at the gate or skipped was indistinguishable from a
  publish by exit status.
- The 2026-10-02 run met a Collector brief of schema 3 while the consumer expected
  schema 2. Every unit was marked invalid, the gate blocked, the workflow run
  concluded `success`, and the Registry `block_reason` carried only the generic
  `integrity_status=invalid (ancestry_reconciliation)` template. The specific
  diagnostic (`schema_version=3, expected 2`) reached only the run log (`[B-072]`).
- Four consecutive scheduled runs (2026-10-11 to 2026-10-14) concluded `success`
  with an automation-only skip and no Registry record. The Registry alone cannot
  show that those runs happened (`[B-076]`).
- After a confirmed publish, the identity-state append and the Registry write ran
  in sequence with no separation. A failure in either surfaced as an unstructured
  traceback. A `block` record already present for the same `content_id` makes the
  later `pass` write fail on disagreement (`publication_registry/writer.py`,
  outcome 4), after the post is already live.
- Through the real Collector adapter and `pre_filter`, a valid unit is always
  `include` (`integrity_status=valid`, `corroboration_status=not_applicable`). A
  gate block caused only by non-integrity exclusion of valid units is therefore not
  producible from real Collector data today.
- `PublicationRecord.gate_status` is `Literal["pass", "block"]` (SPEC.md FR1/FR9).

## Decision

**1. Seven outcomes, one per run.**

| Outcome | Exit |
|---|---|
| `PUBLISHED` | 0 |
| `SKIPPED_NO_ELIGIBLE_CONTENT` | 0 |
| `SKIPPED_SAFETY_PAUSE` | 0 |
| `SKIPPED_ALREADY_PUBLISHED` | 0 |
| `SKIPPED_AUTOMATION_ONLY` | 0 |
| `FAILED_INTEGRITY` | 1 |
| `FAILED` | 1 |

**2. Decision order.** (a) An open SAFETY_PAUSE skips the run, before any I/O. (b)
After the existing pass-record check, an existing successful publication wins:
`SKIPPED_ALREADY_PUBLISHED`, even when invalid input is found in the same run. (c)
The bootstrap gate keeps its mechanism (`zero_included_units`) unchanged. When it
blocks and an excluded unit is `integrity_status=invalid`, the outcome is
`FAILED_INTEGRITY`: no model call, no publish call, no block `PublicationRecord`,
and the specific diagnostic of each such unit (its `integrity_check_detail`, for
example the actual and expected schema versions) is kept in the run outcome. (d)
When it blocks and no excluded unit is an integrity violation, the outcome is
`SKIPPED_NO_ELIGIBLE_CONTENT` and the block record is written (SPEC.md FR9). (e)
Otherwise the existing authoring and publication flow continues, and an
automation-only response is `SKIPPED_AUTOMATION_ONLY`. (f) Any unexpected failure is
`FAILED`.

**3. The constraint on FAILED_INTEGRITY.** `FAILED_INTEGRITY` fires only on a gate
block caused by a confirmed integrity violation; existing per-unit exclusion with
valid-unit continuation is unchanged. A run with at least one included unit still
excludes its invalid units and publishes from the valid ones, exactly as before.

**4. The outcome is additional signal.** `PublicationRecord.gate_status` stays
`pass`/`block`; no third value is introduced and the schema is unchanged.
`FAILED_INTEGRITY` and `SKIPPED_AUTOMATION_ONLY` write no Registry record.
`SKIPPED_AUTOMATION_ONLY` follows `[B-076]` only in that nothing here pre-empts its
separate record type: `[B-076]` is a filed decision with no implementation, so no
record is written for that outcome by this decision.

**5. Publication and persistence are separate events.** After `publish_post`
returns, the identity-state append and the Registry write are attempted
independently, and a failure of one never skips the other. If either fails, the run
is `FAILED` with `publication: confirmed`, the post URL and each failed stage kept
in the diagnostics. Nothing in the run retries, and no second `publish_post` call
is made.

**6. Exposure.** The product code prints `OUTCOME=<name> exit_code=<n>` and, when
the environment variable `RUN_OUTCOME_PATH` is set, writes the outcome as JSON to
that path. The path is deliberately outside the Registry output directory: an
outcome file there would be a second source of truth beside `PublicationRecord`.
Rendering the outcome in the scheduled workflow's job summary, and persisting the
Registry and state files on a failed run, belong to the runtime repository and are
not described further here (ADR-0064, point 3).

**7. Retention limit, stated plainly.** The `FAILED_INTEGRITY` diagnostic lives only
in the run outcome, the job summary and the run log, within whatever GitHub Actions
retention is configured for the repository. It is not retained permanently and is
not a durable archive. The run log always carries it; the job summary and the outcome
file exist only once the calling workflow exposes them (the runtime workflow change
is not applied at the time of this record). The product code states this limit in
the run output and in the outcome file.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Treat any `integrity_status=invalid` unit as a failure, even when other units are included | Not chosen. It changes the existing per-unit exclusion policy and would turn a day that can still publish from valid units into a failed run. |
| B. Keep the gate block as exit 0 and only improve `block_reason` | Not chosen. A schema mismatch would stay a green run, which is the observation in `[B-072]`. |
| C. Write a `block` record for `FAILED_INTEGRITY` too | Not chosen. A block record at the `content_id` makes a later same-day `pass` write fail on disagreement after the post is live. The diagnostic is not lost: it is in the run outcome, which is also the case for the automation-only skip. |
| D. Add a Registry outcome type or a third `gate_status` value now | Not chosen. It is the open design of `[B-076]`, whose consumer inventory has not been done. |
| E. Chosen — the seven-outcome contract in product code, `gate_status` unchanged, the outcome exposed through stdout and an optional outcome file | Smallest change that makes each run's result explicit without a second source of truth in the Registry. |

On ADR-0056: its Decision (an unknown `schema_version` makes every unit invalid with
no API call) is unchanged and not reversed. What changes is how a day blocked for that
reason is reported: as `FAILED_INTEGRITY` with exit 1 and no block record, not as a
successful run with a block record. Its Consequences statement that an old-shape
brief "blocks (fail closed) rather than crashing" described the exit status at that
time. This record treats that as a reporting change, not a change of the decision,
and does not supersede ADR-0056; no publish occurs in either deployment order. That
judgment is this record's own and is open to the owner.

## Not decided here

- The `[B-076]` record type and any Registry consumer change.
- `[B-069]`'s pre-call guard, and `[B-073]`'s question of what the model's
  automation-only decision depends on.
- A check that the Collector and consumer schema constants agree (`[B-072]` stays
  open).
- Any guard against a manual re-run of a day whose publish was confirmed but whose
  Registry record did not persist. No such guard exists: such a re-run finds no
  `pass` record and would publish again. The diagnostic keeps the URL so the owner
  can see the post is live.
- A same-day re-run after a `SKIPPED_NO_ELIGIBLE_CONTENT` block record that then
  publishes still fails on the existing `block`/`pass` disagreement. Unchanged here.

## Consequences

- A schema-incompatible or otherwise integrity-failed day is a red run with the
  specific diagnostic, not a green run with a generic label.
- Skipped days are named in the run output, not only by the absence of a record.
- A gate block with a valid day and nothing eligible still exits 0 and writes the
  block record; SPEC.md FR9 is clarified accordingly and FR41 records the contract.
- Tests that expected an exception from `main()` now call `run()`; `main()` returns
  the exit code.
- The scheduled workflow must expose the outcome and must persist Registry and state
  files on a failed run; until it does, only the run log carries the outcome.
- Rollout order: the runtime workflow change is applied before or together with the
  product code, never after. On the `FAILED` persistence path the local Registry and
  state writes can partly succeed before the run exits 1, and the previous workflow's
  commit step is skipped after a failed step, which drops that state silently.

## Confirmation & Revisit

**Pending. Not confirmed by a real run.** Confirmed locally by the test suite in
`linkedin_publisher/test_daily_publish.py` (every outcome, the integrity-only gate
trigger, the persistence separation). To be filled in after the first scheduled run
on a workflow that exposes the outcome: the literal run log or job summary showing
`OUTCOME=` for that run.

Revisit if `[B-076]` introduces a Registry outcome record, if the Collector adapter
gains a non-integrity reason to exclude a valid unit, or if a durable store for run
diagnostics is introduced.

**Source.** Owner decision of 2026-10-15 on the reconciliation plan for `[B-072]`,
including two corrections (integrity-only gate trigger; stated retention limit); the
state read directly from the code, the Registry writer, the test file and the
scheduled runs' logs on that date. No external AI contributed.
