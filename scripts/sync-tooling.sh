#!/usr/bin/env bash
# Manual sync helper: installs the ToolTempest primitives pinned in
# .tooltempest.lock into ~/.claude/ (and, for scripts/ and schemas/,
# into this repo). Human-triggered only — no discovery, no
# auto-update. See D-026/D-027/D-028.
#
# The vendored-file list is read from ToolTempest's own MANIFEST.txt
# at the pinned commit (ADR-0006, mikkiola/tooltempest) rather than
# hardcoded here — see docs/BACKLOG.md, "P1 — sync-tooling.sh
# completeness testing (Phase 5)". Destination is derived from each
# entry's top-level directory: skills/ and rules/ are Claude Code
# client config, copied into ~/.claude/; scripts/ and schemas/ are
# consumed directly by this repo's own tooling, copied into this repo.
# docs/reference/ (ToolTempest ADR-0008) is neither: per ToolTempest's
# README ("Reference documentation"), this category is consulted in
# place, not installed as a rule -- this project's own convention
# (docs/BACKLOG.md, docs/adr/0044) already cites documentation-rules.md
# by its ToolTempest path rather than vendoring a local copy, so
# sync-tooling.sh recognizes and skips it rather than copying it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="${REPO_ROOT}/.tooltempest.lock"
CACHE_DIR="${HOME}/.cache/tooltempest/repo"
REMOTE_URL="https://github.com/mikkiola/tooltempest.git"
CLAUDE_DIR="${HOME}/.claude"
MANIFEST_NAME="MANIFEST.txt"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$LOCK_FILE" ] || fail "lock file not found at ${LOCK_FILE}"

PINNED_SHA="$(grep '"commit"' "$LOCK_FILE" | sed -E 's/.*"commit"[[:space:]]*:[[:space:]]*"([0-9a-f]+)".*/\1/')"
[ -n "$PINNED_SHA" ] || fail "could not parse \"commit\" out of ${LOCK_FILE}"
[[ "$PINNED_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "pinned commit \"${PINNED_SHA}\" is not a valid 40-char SHA"

echo "Pinned commit: ${PINNED_SHA}"

# BEGIN CACHE PREPARATION
# Cache writes are permitted; installation destinations remain untouched.
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
# END CACHE PREPARATION

# BEGIN READ-ONLY PREFLIGHT
# Validate the complete prepared manifest before creating or copying any
# installation target. Compare the same source files cp will use below.
MANIFEST_FILE="${CACHE_DIR}/${MANIFEST_NAME}"
[ -f "$MANIFEST_FILE" ] || fail "${MANIFEST_NAME} not found in ToolTempest at ${PINNED_SHA} (expected at repo root)"

INSTALL_FILES=()
INSTALL_DESTINATIONS=()
CONFLICTS=()
SKIPPED_COUNT=0
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  case "$rel" in
    skills/*|rules/*) dest="${CLAUDE_DIR}/${rel}" ;;
    scripts/*|schemas/*) dest="${REPO_ROOT}/${rel}" ;;
    docs/reference/*)
      echo "SKIP: ${rel} is reference documentation (ToolTempest ADR-0008) -- consulted in place, not vendored"
      SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
      continue
      ;;
    *)
      fail "MANIFEST.txt entry \"${rel}\" is outside the known skills/rules/scripts/schemas/docs-reference destinations -- update sync-tooling.sh's mapping before proceeding"
      ;;
  esac
  [ -f "${CACHE_DIR}/${rel}" ] \
    || fail "pinned source unavailable: ${rel} (no installation destinations written)"
  INSTALL_FILES+=("$rel")
  INSTALL_DESTINATIONS+=("$dest")
done < "$MANIFEST_FILE"
[ "$((${#INSTALL_FILES[@]} + SKIPPED_COUNT))" -gt 0 ] \
  || fail "${MANIFEST_NAME} at ${PINNED_SHA} lists no files"
for ((i=0; i<${#INSTALL_FILES[@]}; i++)); do
  rel="${INSTALL_FILES[$i]}"
  dest="${INSTALL_DESTINATIONS[$i]}"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if ! cmp -s "${CACHE_DIR}/${rel}" "$dest"; then
      CONFLICTS+=("$dest")
    fi
  fi
done
if [ "${#CONFLICTS[@]}" -gt 0 ]; then
  echo "FAIL: divergent sync destinations (no installation destinations written):" >&2
  printf '  - %s\n' "${CONFLICTS[@]}" >&2
  fail "reconcile the pinned source and destination contents before retrying; sync will not overwrite divergent files"
fi
# END READ-ONLY PREFLIGHT

# BEGIN INSTALL TARGETS
INSTALLED_COUNT=0
for ((i=0; i<${#INSTALL_FILES[@]}; i++)); do
  rel="${INSTALL_FILES[$i]}"
  dest="${INSTALL_DESTINATIONS[$i]}"
  mkdir -p "$(dirname "$dest")"
  cp "${CACHE_DIR}/${rel}" "$dest" || fail "failed to copy ${rel}"
  INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
done
# END INSTALL TARGETS

echo "OK: installed ${INSTALLED_COUNT} ToolTempest file(s), skipped ${SKIPPED_COUNT} reference doc(s) (commit ${ACTUAL_SHA}) per ${MANIFEST_NAME} into ${REPO_ROOT} and ${CLAUDE_DIR}"
exit 0
