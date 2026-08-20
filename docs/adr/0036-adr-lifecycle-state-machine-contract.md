# ADR-0036: ADR Lifecycle State Machine Contract

Status: Accepted
Relates to: `docs/BACKLOG.md`'s "P2 — ADR lifecycle state machine +
structural validation + generated index" entry, which this ADR resolves
the "needs its own ADR before implementation" gate for. Does not extend
or edit any prior ADR.

## Context

`docs/BACKLOG.md` flagged that ADR status is currently free-text and
unenforced: no automated check confirms a new ADR's number is unique,
that a "Supersedes" relationship is followed through (the superseded
ADR's own Status line actually updated to say so), or that status
transitions are valid. That entry split the work into two pieces and
explicitly deferred the larger one: "Do not implement this piece without
a preceding ADR describing the lifecycle contract itself — decided this
session, per the discussion of Log4brains/MADR-style tooling as prior
art." This ADR is that preceding ADR. It describes the contract only;
it does not implement the state machine, the field pair, or the
generated index — those remain separate, later implementation work, per
`docs/BACKLOG.md`'s explicit sequencing rule and DocOps SPEC.md's M5
milestone (2026-08-20), which scoped this ADR to a proposal precisely
so implementation wouldn't get ahead of its acceptance.

Two related, smaller pieces are explicitly out of this ADR's scope:
`docs/CONSTITUTION.md`'s existing "ADRs are never edited after
acceptance" rule (unchanged, this ADR doesn't touch it), and the
lightweight numbering/filename-match check (`scripts/
check_adr_numbering.py`, DocOps SPEC.md M5's other half) — that piece
needed no preceding ADR and is already implemented separately, in the
same commit that adds this file.

## Decision

Three elements, together forming the lifecycle contract:

1. **An explicit `Status` state machine**: `Proposed` → `Accepted` →
   (optionally) `Deprecated` or `Superseded`. `Proposed` is new — every
   existing ADR in this repo currently reads `Status: Accepted` directly,
   with no prior `Proposed` stage on record; this ADR does not
   retroactively require rewriting them (that would violate Immutable
   Lineage, ADR-0011) — the state machine applies going forward.
2. **An explicit `Supersedes` / `Superseded by` field pair.** When a new
   ADR supersedes an old one, the new ADR's own field set gains a
   `Supersedes: ADR-NNNN` line, and — the part currently done only by
   convention, per ADR-0035's own callout of this gap — the *old* ADR's
   `Status` line is expected to be updated to `Superseded by ADR-MMMM`.
   `docs/CONSTITUTION.md`'s "never edited after acceptance" rule already
   carves out exactly this exception implicitly ("a changed decision
   becomes a new ADR that supersedes the old one" presupposes the old
   one's Status line changes to record that) — this ADR makes it an
   explicit, checkable field rather than relying on prose recognition.
   ADR-0035's own precedent (superseding two *points* inside ADR-0033,
   not the whole file) is the harder case this field pair does not
   solve: point-level supersession isn't representable in a single
   file-level `Supersedes` field. This ADR's Decision does not resolve
   that case; a future ADR may need a point-level annotation convention
   if it recurs.
3. **A generated `docs/adr/ADR-INDEX.md`**, derived from the two fields
   above (never hand-maintained) — one row per ADR: number, title,
   status, supersedes/superseded-by if any. Matches Log4brains/MADR-style
   tooling's precedent of treating the index as a build artifact, not a
   source of truth.

## Options considered

| Option | Pros | Cons | Risks |
|---|---|---|---|
| A. Chosen: `Proposed`/`Accepted`/`Deprecated`/`Superseded` state machine + explicit field pair + generated index | Matches established prior art (Log4brains/MADR); makes supersession machine-checkable instead of prose-only; the generated index can't drift from the ADRs themselves, since it's derived | Requires implementation work (CI enforcement, index generator) not done in this ADR; existing ADRs all read `Accepted` with no `Proposed` history, so the state machine only binds new ADRs going forward | A CI check enforcing field-pair consistency could false-positive on ADR-0035's point-level supersession case, which this contract doesn't model — must be scoped explicitly to file-level supersession when implemented |
| B. Status quo — free-text `Status`, no field pair, no generated index | No new implementation burden | The exact gap `docs/BACKLOG.md` flagged remains open indefinitely | Rejected: doesn't resolve the entry this ADR exists to unblock |
| C. Full automation now (this ADR both decides and implements) | Closes the gap in one pass | Directly contradicts `docs/BACKLOG.md`'s own explicit sequencing rule ("do not implement... without a preceding ADR") — this ADR's entire purpose is to be that preceding step, not to skip it | Rejected: the sequencing rule exists specifically so the contract is decided independently of a rushed implementation pass |

## Chosen

A.

## Why

Option A is the only one that actually closes the gap `docs/BACKLOG.md`
flagged while respecting that entry's own explicit sequencing
requirement — a contract decided on its own, separately from
implementation pressure, mirroring the prior art already discussed
(Log4brains/MADR treat status and the index the same way). Option B
leaves a known, already-diagnosed gap open with no path forward. Option
C treats the sequencing rule as an obstacle to route around rather than
the reason this ADR exists.

## Constraints

Does not implement the state machine, the field pair, or the index
generator — that is separate, later work, deliberately not bundled into
the same commit that decides this contract. Does not retroactively
rewrite any existing ADR's `Status` line. Does not resolve ADR-0035's
point-level supersession case — noted as an open gap in the field pair's
design, not solved here. Does not change `docs/CONSTITUTION.md`'s
existing "never edited after acceptance" rule.

## Rejected

B — rejected because it leaves the diagnosed gap open indefinitely, with
no stated path to closing it. C — rejected because it contradicts the
explicit sequencing rule this ADR exists to satisfy: deciding the
contract in the same pass as implementing it would repeat exactly the
"contract decided under implementation pressure" failure mode
`docs/BACKLOG.md`'s entry was written to avoid.

## Consequences

- `docs/BACKLOG.md`'s "ADR lifecycle state machine + structural
  validation + generated index" P2 entry's second (full-design) piece
  is now unblocked — a future task can implement the CI enforcement and
  index generator against this contract without re-deciding its shape.
- Every ADR from this point forward may declare `Status: Proposed`
  before `Accepted`; existing ADRs (0001–0035) are unaffected and are
  not retroactively required to have had a `Proposed` stage.
- A future CI check enforcing the `Supersedes`/`Superseded by` field
  pair must explicitly exclude or special-case ADR-0035's point-level
  supersession pattern, since this contract only models whole-file
  supersession.

## Validation

Deferred to the future implementation task this ADR unblocks — no CI
enforcement, index generator, or field-pair check is implemented or
tested here. This ADR is validated by review/acceptance of the contract
itself, not by running code.

## Reversal condition

If implementing the field pair or generated index surfaces a
contract-level problem this ADR didn't anticipate (for example, the
point-level supersession gap proving common rather than rare), revisit
this ADR rather than patching around it silently in the implementation.

## Source

DocOps SPEC.md M5 (2026-08-20), resolving the "needs its own ADR before
implementation" gate `docs/BACKLOG.md`'s P2 entry set for this work,
per that entry's own reference to the Log4brains/MADR-style tooling
discussion.
