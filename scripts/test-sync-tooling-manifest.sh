#!/usr/bin/env bash
# Regression test for BACKLOG.md "P1 -- sync-tooling.sh completeness testing
# (Phase 5)": verify every file listed in ToolTempest's own MANIFEST.txt (at
# the commit pinned in .tooltempest.lock) actually exists in the ToolTempest
# repo at that commit. Catches typos/renames/deletions surfacing as a
# MANIFEST.txt entry that no longer resolves to a real file.
#
# Reads MANIFEST.txt instead of parsing scripts/sync-tooling.sh's cp lines
# (the previous approach): as of the ADR-0005/ADR-0006 repin,
# sync-tooling.sh no longer has a static per-file cp list to parse -- it
# loops over MANIFEST.txt directly (see this same BACKLOG entry).
# Completeness of *which* files MANIFEST.txt should list is ToolTempest's
# own concern, guarded on that side by scripts/check_manifest.py
# (ADR-0006); this test is the consumer-side counterpart, confirming every
# entry MANIFEST.txt does list is real at the pinned commit.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="${REPO_ROOT}/.tooltempest.lock"
CACHE_DIR="${HOME}/.cache/tooltempest/repo"
REMOTE_URL="https://github.com/mikkiola/tooltempest.git"
MANIFEST_NAME="MANIFEST.txt"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$LOCK_FILE" ] || fail "lock file not found at ${LOCK_FILE}"

PINNED_SHA="$(grep '"commit"' "$LOCK_FILE" | sed -E 's/.*"commit"[[:space:]]*:[[:space:]]*"([0-9a-f]+)".*/\1/')"
[ -n "$PINNED_SHA" ] || fail "could not parse \"commit\" out of ${LOCK_FILE}"
[[ "$PINNED_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "pinned commit \"${PINNED_SHA}\" is not a valid 40-char SHA"

if [ -d "${CACHE_DIR}/.git" ]; then
  git -C "${CACHE_DIR}" fetch --quiet origin "$PINNED_SHA" || fail "git fetch of ${PINNED_SHA} failed"
else
  mkdir -p "$(dirname "${CACHE_DIR}")"
  git clone --quiet "$REMOTE_URL" "$CACHE_DIR" || fail "git clone failed"
fi

MANIFEST_CONTENT="$(git -C "${CACHE_DIR}" show "${PINNED_SHA}:${MANIFEST_NAME}" 2>/dev/null)" \
  || fail "${MANIFEST_NAME} not found in ToolTempest at ${PINNED_SHA}"

# Portable array read, not `mapfile` -- macOS ships bash 3.2, which lacks it.
VENDORED_FILES=()
while IFS= read -r line; do
  [ -n "$line" ] && VENDORED_FILES+=("$line")
done <<< "$MANIFEST_CONTENT"
[ "${#VENDORED_FILES[@]}" -gt 0 ] || fail "${MANIFEST_NAME} at ${PINNED_SHA} lists no files"

MISSING=()
for f in "${VENDORED_FILES[@]}"; do
  if ! git -C "${CACHE_DIR}" cat-file -e "${PINNED_SHA}:${f}" 2>/dev/null; then
    MISSING+=("$f")
  fi
done

if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "FAIL: ${#MISSING[@]} file(s) listed in ${MANIFEST_NAME} do not exist in ToolTempest at ${PINNED_SHA}:" >&2
  for f in "${MISSING[@]}"; do
    echo "  - ${f}" >&2
  done
  exit 1
fi

echo "OK: all ${#VENDORED_FILES[@]} file(s) listed in ${MANIFEST_NAME} exist in ToolTempest at ${PINNED_SHA}."
exit 0
