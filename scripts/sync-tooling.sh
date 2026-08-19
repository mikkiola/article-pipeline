#!/usr/bin/env bash
# Manual sync helper: installs the ToolTempest primitives pinned in
# .tooltempest.lock into ~/.claude/. Human-triggered only — no
# discovery, no auto-update. See D-026/D-027/D-028.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="${REPO_ROOT}/.tooltempest.lock"
CACHE_DIR="${HOME}/.cache/tooltempest/repo"
REMOTE_URL="https://github.com/mikkiola/tooltempest.git"
CLAUDE_DIR="${HOME}/.claude"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$LOCK_FILE" ] || fail "lock file not found at ${LOCK_FILE}"

PINNED_SHA="$(grep '"commit"' "$LOCK_FILE" | sed -E 's/.*"commit"[[:space:]]*:[[:space:]]*"([0-9a-f]+)".*/\1/')"
[ -n "$PINNED_SHA" ] || fail "could not parse \"commit\" out of ${LOCK_FILE}"
[[ "$PINNED_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "pinned commit \"${PINNED_SHA}\" is not a valid 40-char SHA"

echo "Pinned commit: ${PINNED_SHA}"

if [ -d "${CACHE_DIR}/.git" ]; then
  echo "Using existing cache at ${CACHE_DIR}"
  git -C "${CACHE_DIR}" fetch --quiet origin "$PINNED_SHA" || fail "git fetch of ${PINNED_SHA} failed"
else
  echo "Cloning ${REMOTE_URL} into ${CACHE_DIR}"
  mkdir -p "$(dirname "${CACHE_DIR}")"
  git clone --quiet "$REMOTE_URL" "$CACHE_DIR" || fail "git clone failed"
fi

git -C "${CACHE_DIR}" checkout --quiet --detach "$PINNED_SHA" || fail "checkout of ${PINNED_SHA} failed"

ACTUAL_SHA="$(git -C "${CACHE_DIR}" rev-parse HEAD)"
[ "$ACTUAL_SHA" = "$PINNED_SHA" ] || fail "checked-out SHA (${ACTUAL_SHA}) does not match lock file (${PINNED_SHA})"

mkdir -p "${CLAUDE_DIR}/skills/spec" "${CLAUDE_DIR}/skills/verify" "${CLAUDE_DIR}/rules"

cp "${CACHE_DIR}/skills/spec/SKILL.md" "${CLAUDE_DIR}/skills/spec/SKILL.md" || fail "failed to copy skills/spec/SKILL.md"
cp "${CACHE_DIR}/skills/verify/SKILL.md" "${CLAUDE_DIR}/skills/verify/SKILL.md" || fail "failed to copy skills/verify/SKILL.md"
cp "${CACHE_DIR}/rules/drift-control.md" "${CLAUDE_DIR}/rules/drift-control.md" || fail "failed to copy rules/drift-control.md"

echo "OK: installed ToolTempest V1 primitives (commit ${ACTUAL_SHA}) into ${CLAUDE_DIR}"

# DocOps Protocol (ADR-0001, ToolTempest V2; Tier 2 per ADR-0002).
# scripts/doc_sync.py and schemas/execution-record.schema.json are
# executable/reference material consumed by this project's own git
# hooks. scripts/doc_sync_tier2.py is invoked directly by the agent's
# own judgment (ADR-0002c), not by a git hook, but is vendored here for
# the same reason: it needs to exist inside this repo, not only in
# ~/.claude/.
# skills/doc-sync/SKILL.md is Claude Code client config, like the V1
# skills above, so it follows the same ~/.claude/ path.
mkdir -p "${REPO_ROOT}/scripts" "${REPO_ROOT}/schemas" "${CLAUDE_DIR}/skills/doc-sync"

cp "${CACHE_DIR}/scripts/doc_sync.py" "${REPO_ROOT}/scripts/doc_sync.py" || fail "failed to copy scripts/doc_sync.py"
cp "${CACHE_DIR}/scripts/doc_sync_tier2.py" "${REPO_ROOT}/scripts/doc_sync_tier2.py" || fail "failed to copy scripts/doc_sync_tier2.py"
cp "${CACHE_DIR}/schemas/execution-record.schema.json" "${REPO_ROOT}/schemas/execution-record.schema.json" || fail "failed to copy schemas/execution-record.schema.json"
cp "${CACHE_DIR}/skills/doc-sync/SKILL.md" "${CLAUDE_DIR}/skills/doc-sync/SKILL.md" || fail "failed to copy skills/doc-sync/SKILL.md"

echo "OK: installed ToolTempest DocOps Protocol (commit ${ACTUAL_SHA}) into ${REPO_ROOT} and ${CLAUDE_DIR}"
exit 0
