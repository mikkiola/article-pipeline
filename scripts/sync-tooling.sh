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

echo "OK: installed ToolTempest commit ${ACTUAL_SHA} into ${CLAUDE_DIR}"
exit 0
