---
id: ADR-0016
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# 0016 — Git authentication via gh/glab CLI, not raw tokens in chat

## Status

ACTIVE. Implemented and confirmed.

## Context & Constraints

A token pasted directly into a chat exists outside the project's secret
registry, with no record of where it lives or who has seen it — the
project has no formal secret registry to begin with, which makes this
risk worse, not better. CLI-managed auth keeps the credential in a
single, OS-managed location instead of scattered across chat history.

No raw token should ever appear in a chat message with Claude Code going
forward, for any git operation.

## Decision

Use `gh auth login` / `glab auth login`; credentials live in the macOS
system keychain.

## Alternatives & Rationale

A — paste a personal access token directly into chat with Claude Code.
B — gh/glab CLI with system keychain storage (chosen).

B.

A — creates an untracked secret outside any registry, discovered only by
incident.

## Consequences

Implemented and used successfully for two separate pushes: 2026-08-10
(commit `e7fbc45`) and 2026-08-13 (Evidence Package push via GitHub CLI
auth).

## Confirmation & Revisit

Confirmed — both pushes succeeded through this mechanism.

None specified.

**Source.** Triggered by an incident (no working credentials existed at all for one
account) plus explicit owner decision.
