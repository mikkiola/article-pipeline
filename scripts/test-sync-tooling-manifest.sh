#!/usr/bin/env bash
# Regression test for BACKLOG.md "P1 -- sync-tooling.sh completeness testing
# (Phase 5)", piece 1 only: verify every file scripts/sync-tooling.sh vendors
# from ToolTempest actually exists in the ToolTempest repo at the commit
# pinned in .tooltempest.lock. Catches typos/renames/deletions in the
# existing vendored-file list. Does NOT and cannot catch a new ToolTempest
# file that should be added to the list but isn't -- that is piece 2
# (completeness design), a separate, not-yet-decided architectural task.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="${REPO_ROOT}/.tooltempest.lock"
SYNC_SCRIPT="${REPO_ROOT}/scripts/sync-tooling.sh"
CACHE_DIR="${HOME}/.cache/tooltempest/repo"
REMOTE_URL="https://github.com/mikkiola/tooltempest.git"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$LOCK_FILE" ] || fail "lock file not found at ${LOCK_FILE}"
[ -f "$SYNC_SCRIPT" ] || fail "sync script not found at ${SYNC_SCRIPT}"

PINNED_SHA="$(grep '"commit"' "$LOCK_FILE" | sed -E 's/.*"commit"[[:space:]]*:[[:space:]]*"([0-9a-f]+)".*/\1/')"
[ -n "$PINNED_SHA" ] || fail "could not parse \"commit\" out of ${LOCK_FILE}"
[[ "$PINNED_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "pinned commit \"${PINNED_SHA}\" is not a valid 40-char SHA"

# Every source path sync-tooling.sh copies from ${CACHE_DIR}/<path>.
# (Portable array read, not `mapfile` -- macOS ships bash 3.2, which lacks it.)
VENDORED_FILES=()
while IFS= read -r line; do
  VENDORED_FILES+=("$line")
done < <(grep -E '^\s*cp "\$\{CACHE_DIR\}/' "$SYNC_SCRIPT" | grep -oE '\$\{CACHE_DIR\}/[^"]+' | sed -E 's#^\$\{CACHE_DIR\}/##' | sort -u)
[ "${#VENDORED_FILES[@]}" -gt 0 ] || fail "no vendored files found in ${SYNC_SCRIPT} (unexpected -- parsing may be broken)"

if [ -d "${CACHE_DIR}/.git" ]; then
  git -C "${CACHE_DIR}" fetch --quiet origin "$PINNED_SHA" || fail "git fetch of ${PINNED_SHA} failed"
else
  mkdir -p "$(dirname "${CACHE_DIR}")"
  git clone --quiet "$REMOTE_URL" "$CACHE_DIR" || fail "git clone failed"
fi

MISSING=()
for f in "${VENDORED_FILES[@]}"; do
  if ! git -C "${CACHE_DIR}" cat-file -e "${PINNED_SHA}:${f}" 2>/dev/null; then
    MISSING+=("$f")
  fi
done

if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "FAIL: ${#MISSING[@]} file(s) listed in ${SYNC_SCRIPT} do not exist in ToolTempest at ${PINNED_SHA}:" >&2
  for f in "${MISSING[@]}"; do
    echo "  - ${f}" >&2
  done
  exit 1
fi

echo "OK: all ${#VENDORED_FILES[@]} vendored file(s) in ${SYNC_SCRIPT} exist in ToolTempest at ${PINNED_SHA}."
exit 0
