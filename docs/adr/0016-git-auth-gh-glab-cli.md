# 0016 — Git authentication via gh/glab CLI, not raw tokens in chat

## Status
Accepted. Implemented and confirmed.

## Context

Pasting a personal access token directly into a chat with Claude Code
creates a secret that exists outside the project's secret registry
(which does not otherwise exist as a formal artifact).

## Decision

Use `gh auth login` / `glab auth login`; credentials live in the macOS
system keychain.

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
