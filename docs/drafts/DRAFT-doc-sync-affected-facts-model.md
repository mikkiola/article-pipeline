# Doc-Sync "Affected Facts" Model — DRAFT

**Status: DRAFT**
This document is not an architectural decision and does not override
or commit to anything currently implemented by `scripts/doc_sync.py`
or any other automation-track script. Anything marked OPEN below is
genuinely undecided — a future session should not treat it as settled
by virtue of appearing in this file.

This is a captured idea for a future, more general documentation-
synchronization pipeline. It is not implementation, not a task to
execute now, and not a plan a session should pick up without a
deliberate decision to do so first.

## 1. Overview

The core model, stated plainly:

```
change (code commit / SPEC edit / validation result)
  -> classify which canonical-doc facts are affected
    -> for each affected fact, determine its derivation class:
         - safe, deterministic derivation exists
           (e.g. Step 8's Commit-column pattern)
         - requires human/architectural judgment
           (e.g. Status / Depends on / Validation)
    -> propose a diff for the derivable ones
    -> surface the rest for explicit human decision
```

The origin of this idea is explicit: it generalizes the two narrow,
independently hard-coded mechanical-fix patterns Step 8 already
implements — the Files-enumeration append and the single-SHA
Commit-column update — into a single named concept, a fact's
**derivation class**, rather than two separate ad hoc functions each
re-deriving from scratch whether they're allowed to act. Under this
model, adding a third safe pattern in the future would mean
classifying a new kind of fact into the existing derivation-class
framework, not writing a third bespoke detector function with its own
independent judgment-call reasoning duplicated inside it.

Nothing here asserts that generalizing is worth doing, or that the
current two-function approach is inadequate. Step 8 works today with
exactly the scope it needed. This draft exists so the generalization
idea isn't lost, not to argue it's the next priority.

## 2. Why this is a DRAFT, not an ADR yet

No implementation exists beyond what Step 8 already built (which this
draft explicitly does not re-describe as if it were new — see §3). No
experiment has validated that a general "derivation class" abstraction
is actually cleaner than two hard-coded functions once a third pattern
is needed — that comparison can't be made honestly until a third
pattern is actually attempted. This is a captured idea for a future
session to pick up deliberately, evaluate against a real second or
third use case, and only then decide whether it earns an ADR. Writing
an ADR now would assert a decision that hasn't been tested against
reality yet.

## 3. Relationship to Steps 1-8 (already built, not proposed by this draft)

`scripts/checklist.py`, `harness.py`, `drift.py`, `doc_impact.py`, and
`doc_sync.py` already exist and already implement pieces of a
narrower version of this model, for exactly two generated artifacts
(checklists, harness results) and exactly two canonical-doc patterns
in `docs/ARCHITECTURE.md` (a pure `### Files: <component>` list
append; a single-SHA Commit-cell update). All of that is real,
committed, tested code — this draft does not re-describe it as a
proposal. This draft is only about whether the underlying *shape*
those two patterns share (check a fact's derivation class, act only
if it's safely deterministic) is worth naming and generalizing for a
future third pattern, not about changing anything that exists today.

## 4. Explicitly NOT in scope for this draft to resolve right now

- **OPEN** — What counts as a "fact" formally. Is it always exactly
  one table cell / one list item, or could a single fact legitimately
  span multiple locations (e.g. a Status cell and a matching sentence
  in a Validation cell that both need to agree)? Step 8's two
  patterns both happen to be single-cell/single-line facts; whether
  that's a coincidence of the two easy cases or a hard constraint of
  the model isn't known.
- **OPEN** — Where the derivation-class boundary sits for Status /
  Depends on / Validation columns specifically. Step 8 treats all
  three as permanently human-judgment-only, by explicit owner
  decision, for this pilot's scope. Whether any of the three could
  ever become mechanically derivable in some future, narrower sense
  (e.g. Status flipping to "Implemented" only when every harness VC
  for that component is DONE and PASS/MANUAL/SKIPPED-only) is not
  decided — see the harness-result-classification P1 BACKLOG item
  this idea partly resembles, without conflating the two.
- **OPEN** — Whether this generalizes to `docs/ROADMAP.md` and
  `docs/BACKLOG.md` as well as `docs/ARCHITECTURE.md`, or is scoped to
  `docs/ARCHITECTURE.md` only. Both other docs have very different
  structure (prose task lists, not a pure fact table) and may not
  admit the same kind of mechanical fact-derivation at all.
- **OPEN** — Trigger granularity: per-commit, per-session, or
  on-demand only. The owner has explicitly flagged the "update docs on
  every chit" churn risk when this idea was raised — a naive
  per-commit trigger could turn every small commit into a doc-sync
  proposal, which is not obviously desirable even when the proposal
  itself is correct. Not decided.
- **OPEN** — Relationship to Step 11 (pre-push integration). Should
  any part of a generalized version of this model ever become
  blocking at push time, or does propose-only (Step 8's current
  contract) stay the permanent design regardless of how general the
  detection gets? Not decided — Step 8's own scope explicitly keeps
  everything propose-only, and this draft does not revisit that.

## 5. Origin

Found/proposed during the automation track's Step 8 (2026-08-18), in
discussion between the architect chat and the owner, following the
discovery that `docs/ARCHITECTURE.md`'s actual, real structure (a pure
fact table — "no prose sections," per the document's own stated
design) had no existing per-component file-enumeration section to
serve as a mechanical-fix target for the originally-planned
Files-enumeration pattern. That discovery — that a seemingly generic
"derived doc update" idea kept needing a different, narrowly-justified
mechanical target depending on which exact doc structure it touched —
is what prompted naming "derivation class" as a potentially reusable
concept, rather than continuing to add one-off functions indefinitely.
