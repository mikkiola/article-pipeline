# 0018 — Personal path privacy in code intended for eventual publication

## Status
ACTIVE. Implemented for non-immutable files.

## Decision
Move personal paths out through an environment variable or a gitignored
config file, for any file that is not an immutable artifact. Immutable
logs (0011) are explicitly not touched.

## Options
A — fix personal paths only right before making the repository public.
B — fix now, while the number of files is still small (chosen).

## Chosen
B.

## Why
`mikkiola/article-pipeline` was created with the explicit intent of
eventually becoming public (0014) — fixing a hardcoded personal path
gets more expensive the more files reference it, so doing it early while
the codebase is still small is cheaper than doing it later under
publication pressure.

## Constraints
Immutable artifacts (0011) are never edited retroactively to remove a
path, even if that path is personal — Immutable Lineage takes priority
over this rule for anything already written as an immutable record.

## Rejected
A — defers a cheap fix until it becomes an expensive one, and risks
rushing it right before publication.

## Consequences
Implemented — `BRAIN_REPO_DIR` resolves through an environment variable
or a gitignored `local_paths.json`. One known remaining gap: a single
immutable pilot log line contains a personal path, intentionally left as
-is because Immutable Lineage (0011) takes priority over this rule.

## Validation
Unverified as a discrete technical check, but referenced as done in a
release record.

## Reversal condition
Not yet triggered — the repository is not public yet.

## Source
Claude Code audit prior to a commit.
