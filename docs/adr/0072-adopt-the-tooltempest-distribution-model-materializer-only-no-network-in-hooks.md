---
id: ADR-0072
status: Accepted
supersedes: ADR-0032
superseded_by: null
source_type: inferred
---

# ADR-0072: Adopt the ToolTempest distribution model: one installer, no network in hooks, one contract file

## Status

Accepted on 2026-11-05. Supersedes ADR-0032 in full. Supersedes ADR-0027 and
ADR-0028 in part, as defined under Decision. The frontmatter `supersedes` field
holds one ID, so it names ADR-0032, the whole-ADR case; the partial supersession
of ADR-0027 and ADR-0028 is stated in prose, following ADR-0035. The superseded
ADRs are not edited (Immutable Lineage), so their `status` and `superseded_by`
stay as accepted.

## Context & Constraints

ToolTempest ADR-0017 (`docs/adr/` of `mikkiola/tooltempest`, accepted
2026-11-04) decides that a consumer gets its ToolTempest files from one
installer, the materializer `scripts/tooling.py`; that consumer hooks make no
network call; and that the consumer obligation lives in one managed contract
file instead of a hand copy per consumer. It leaves to each consumer, in its own
ADR, the removal of the `git ls-remote` drift warning from its pre-push hook.

Before this record, this repository had two installers: `scripts/tooling.py`
and its own `scripts/sync-tooling.sh` (ADR-0027, ADR-0028); a pre-push hook that
called `git ls-remote` against ToolTempest (ADR-0032); and a hand copy of the
consumer obligation in `docs/CONSTITUTION.md` that had fallen behind the
contract (observation at ToolTempest `84519ca`: the copy lacked the repin-evidence
paragraph and the definitions of its terms). The lock format is unchanged by
this record.

## Decision

1. The materializer is the only installer of ToolTempest files in this
   repository. `scripts/sync-tooling.sh` and its tests are removed. A consumer
   workflow that needs installed files runs `tooling.py materialize --apply`
   from the ToolTempest commit pinned in `.tooltempest.lock`.
2. The pre-push hook makes no network call of its own. The `git ls-remote`
   drift warning is removed. Pin freshness is reported by `tooling.py verify` and
   `tooling.py status`, on request.
3. The Constitution links to the managed contract file
   `docs/tooltempest/consumer-contract.md` instead of copying it. The installed
   file is untracked and ignored, like the other installed ToolTempest files.

Parts of earlier ADRs superseded:

- ADR-0032, in full: its decision is the removed drift warning.
- ADR-0027 and ADR-0028, in part. Superseded: the delivery step of ADR-0027's
  Decision ("copying the primitives into the client's environment") is done by
  the materializer, not by a consumer-owned copy script, and the statements that
  `scripts/sync-tooling.sh` implements it (ADR-0027 Consequences and
  Confirmation; ADR-0028 Confirmation) no longer hold. In force, unchanged: the
  lock file records the pinned SHA; delivery is by checkout of that SHA; ADR-0028's
  Decision (discovery may be automatic; installing or activating a version is
  never automatic).

## Alternatives & Rationale

| Option | Verdict |
|---|---|
| A. Keep both installers | Not chosen. Two installers with two destination mappings can disagree; only the materializer writes a receipt and verifies after writing. |
| B. Keep the drift warning, but fetch nothing (read a cached ref) | Not chosen. The hook would still compare commit strings, which says nothing about what changed for this consumer. |
| C. Keep the hand copy and add a comparison check | Not chosen. A check would have to be maintained against a text that already has a single source. |
| D. Chosen: the three changes above | Removes the second installer, the network call and the copy, with no change to the lock format. |

## Consequences

- `docs/tooltempest/consumer-contract.md` does not exist in a fresh clone until
  `tooling.py materialize --apply` runs; the Constitution link points to a file
  that is absent until then.
- The reconciliation workflow no longer installs `skills/` and `rules/` into
  `~/.claude` on its runner; the client files are installed only by the
  explicit `--target client` run, and that workflow does not use them.
- A reader is no longer warned at push time that the pin is behind ToolTempest.
  Freshness stays commit distance until ToolTempest builds its fingerprint
  engine; removed-path handling in installed roots needs its own ADR first
  (both are tracked in `docs/BACKLOG.md`).
- The reconciliation workflow now executes the pinned `tooling.py` in a job with
  `contents: write`; the code comes from the same pinned commit as `doc_sync.py`,
  which that job already ran.

## Confirmation & Revisit

Observed at this repository's commit `e270c03`: `python3 scripts/tooling.py
verify --source <ToolTempest checkout>` exits 0 (local integrity ok, upstream
provenance ok); `grep -c ls-remote scripts/hooks/pre-push` prints 0; the hook
run on an up-to-date push (empty stdin) with a wrapper that logs network-capable
`git` subcommands (`ls-remote`, `fetch`, `clone`, `pull`, `push`, `remote`) logged
none and exited 0. Not confirmed: the network behavior of the `gitleaks` binary
that the hook runs; a GitHub Actions run of the changed reconciliation workflow;
a fetch of the pinned commit from GitHub over the network.

Revisit when the ToolTempest ADR-0017 triggers fire (a fourth consumer
repository; a second incident of a false version signal or of a repin for an
unchanged payload within a quarter; a second AI client; the first removal of a
path of an installed root), or if the reconciliation workflow's fetch of the
pinned commit fails.

**Source.** The Owner's instructions of 2026-11-05, with ToolTempest ADR-0017
as the input decision. No external AI cross-check was made.
