#!/usr/bin/env bash
# Regression test for sync-tooling.sh's destination-mapping "case"
# logic: runs the real script against the current .tooltempest.lock
# pin and confirms every entry in MANIFEST.txt resolves to a real
# destination (or an intentional skip), instead of hitting the
# fail() "is outside the known ... destinations" branch.
#
# Distinct from test-sync-tooling-manifest.sh, which only checks that
# MANIFEST.txt's entries exist in ToolTempest at the pinned commit --
# it never runs sync-tooling.sh itself, so it would not catch a
# destination-mapping gap. That's exactly what happened: MANIFEST.txt
# grew a docs/reference/* entry (ToolTempest ADR-0008) that
# sync-tooling.sh's case statement didn't recognize, so it fell
# through to fail() -- found during [B-061] follow-up work
# (2026-09-14). This test exercises the mapping directly so a future
# unrecognized category is caught here instead.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="${REPO_ROOT}/.tooltempest.lock"
CACHE_DIR="${HOME}/.cache/tooltempest/repo"
CLAUDE_DIR="${HOME}/.claude"
MANIFEST_NAME="MANIFEST.txt"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$LOCK_FILE" ] || fail "lock file not found at ${LOCK_FILE}"

OUTPUT="$("${REPO_ROOT}/scripts/sync-tooling.sh" 2>&1)" && STATUS=0 || STATUS=$?
echo "$OUTPUT"
[ "$STATUS" -eq 0 ] || fail "sync-tooling.sh exited non-zero (see output above)"

if echo "$OUTPUT" | grep -q "is outside the known"; then
  fail "sync-tooling.sh hit its case-statement fail() branch -- see output above"
fi

PINNED_SHA="$(grep '"commit"' "$LOCK_FILE" | sed -E 's/.*"commit"[[:space:]]*:[[:space:]]*"([0-9a-f]+)".*/\1/')"
[ -n "$PINNED_SHA" ] || fail "could not parse \"commit\" out of ${LOCK_FILE}"

MANIFEST_FILE="${CACHE_DIR}/${MANIFEST_NAME}"
[ -f "$MANIFEST_FILE" ] || fail "${MANIFEST_NAME} not found at ${CACHE_DIR} after running sync-tooling.sh"

# Portable array read, not `mapfile` -- macOS ships bash 3.2, which
# lacks it (see the same pattern in sync-tooling.sh).
VENDORED_FILES=()
while IFS= read -r line; do
  [ -n "$line" ] && VENDORED_FILES+=("$line")
done < "$MANIFEST_FILE"
[ "${#VENDORED_FILES[@]}" -gt 0 ] || fail "${MANIFEST_NAME} lists no files"

for rel in "${VENDORED_FILES[@]}"; do
  case "$rel" in
    skills/*|rules/*)
      dest="${CLAUDE_DIR}/${rel}"
      [ -f "$dest" ] || fail "${rel} did not land at expected destination ${dest}"
      ;;
    scripts/*|schemas/*)
      dest="${REPO_ROOT}/${rel}"
      [ -f "$dest" ] || fail "${rel} did not land at expected destination ${dest}"
      ;;
    docs/reference/*)
      # Consulted in place (ToolTempest ADR-0008) -- sync-tooling.sh
      # intentionally skips copying this category. Confirming it
      # didn't hit fail() (checked above) is the whole test here.
      ;;
    *)
      fail "MANIFEST.txt entry \"${rel}\" has no known destination category -- this test needs updating alongside sync-tooling.sh"
      ;;
  esac
done

echo "OK: all ${#VENDORED_FILES[@]} MANIFEST.txt entries resolved via sync-tooling.sh's mapping without hitting fail()."
exit 0
