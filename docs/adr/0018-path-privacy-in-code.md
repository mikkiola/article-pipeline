# 0018 — Personal path privacy in code intended for eventual publication

## Status
Accepted. Implemented for non-immutable files.

## Context

`mikkiola/article-pipeline` was created with the intent of eventually
becoming public (0014). Fixing a hardcoded personal path is cheaper now,
while the number of files is still small.

## Decision

Move personal paths out through an environment variable or a gitignored
config file, for any file that is not an immutable artifact.
Immutable logs (0011) are explicitly not touched.

## Consequences

Implemented — `BRAIN_REPO_DIR` resolves through an environment variable
or a gitignored `local_paths.json`. One known remaining gap: a single
immutable pilot log line contains a personal path, intentionally left
as-is because Immutable Lineage (0011) takes priority over this rule.

## Validation
Unverified as a discrete technical check, but referenced as done in a
release record.

## Reversal condition
Not yet triggered — the repository is not public yet.

## Source
Claude Code audit prior to a commit.
