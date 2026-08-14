# 0027 — Lock file, delivery, and recovery contract for shared tooling

## Status
Accepted. Physically implemented in `mikkiola/article-pipeline` — see
0028 for the renamed lock file and the commit that closed this path.

## Context

Following 0026 (independent canonical repository, pinned by full commit
SHA), each consuming project needs a concrete mechanism to declare and
retrieve the specific version it depends on.

## Decision

A lock file in the consuming project records the pinned commit SHA.
Delivery works by checking out the shared repository at that pinned SHA
and copying the primitives into the client's environment. The installer
itself is not versioned separately — it travels as part of the same
commit it delivers.

**Original lock file name at time of this decision: `.claude-tooling.lock`
— renamed to `.tooltempest.lock` by 0028; see that record for the
renaming rationale. This record's text is not retroactively edited
(Immutable Lineage); the current, correct file name for implementation
is `.tooltempest.lock`.**

## Consequences

Recovery boundary: offline restoration is only possible if the relevant
commit is already present in a local cache
(`~/.cache/tooltempest/<SHA>`) — this is not a promise of full offline
reproducibility from a clean machine with no network and no prior cache.

## Validation
Confirmed by later implementation — see 0028 and the commit it
references (`.tooltempest.lock` plus `scripts/sync-tooling.sh`, tested
end to end with a byte-for-byte diff against the source).

## Reversal condition
None specified independently — bound to 0028's reversal condition, since
the two decisions form one continuous contract.

## Source
Continuation of 0026. Explicit owner decision on the recovery boundary
question.
