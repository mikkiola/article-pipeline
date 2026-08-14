# 0016 — Git authentication via gh/glab CLI, not raw tokens in chat

## Status
ACTIVE. Implemented and confirmed.

## Decision
Use `gh auth login` / `glab auth login`; credentials live in the macOS
system keychain.

## Options
A — paste a personal access token directly into chat with Claude Code.
B — gh/glab CLI with system keychain storage (chosen).

## Chosen
B.

## Why
A token pasted directly into a chat exists outside the project's secret
registry, with no record of where it lives or who has seen it — the
project has no formal secret registry to begin with, which makes this
risk worse, not better. CLI-managed auth keeps the credential in a
single, OS-managed location instead of scattered across chat history.

## Constraints
No raw token should ever appear in a chat message with Claude Code going
forward, for any git operation.

## Rejected
A — creates an untracked secret outside any registry, discovered only by
incident.

## Consequences
Implemented and used successfully for two separate pushes: 2026-08-10
(commit `e7fbc45`) and 2026-08-13 (Evidence Package push via GitHub CLI
auth).

## Validation
Confirmed — both pushes succeeded through this mechanism.

## Reversal condition
None specified.

## Source
Triggered by an incident (no working credentials existed at all for one
account) plus explicit owner decision.
