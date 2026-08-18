#!/usr/bin/env bash
# Installs the DocOps Protocol git hooks (ToolTempest ADR-0001) into
# .git/hooks/. Human-triggered only -- nothing in this repository runs
# it automatically. Running it activates pre-commit reconciliation and
# adds DocOps hard validation to pre-push; until it is run, .git/hooks/
# is left exactly as it already was.
#
# Source of truth for the hook bodies is scripts/hooks/{pre-commit,
# pre-push} in this repository (tracked in git, unlike .git/hooks/
# itself). Re-run this script after pulling a change to either file to
# pick it up.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="${REPO_ROOT}/.git/hooks"
SOURCE_DIR="${REPO_ROOT}/scripts/hooks"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -d "${REPO_ROOT}/.git" ] || fail "${REPO_ROOT} is not a git repository root"
[ -f "${SOURCE_DIR}/pre-commit" ] || fail "source hook not found: ${SOURCE_DIR}/pre-commit"
[ -f "${SOURCE_DIR}/pre-push" ] || fail "source hook not found: ${SOURCE_DIR}/pre-push"

for name in pre-commit pre-push; do
  if [ -f "${HOOKS_DIR}/${name}" ] && ! cmp -s "${HOOKS_DIR}/${name}" "${SOURCE_DIR}/${name}"; then
    backup="${HOOKS_DIR}/${name}.pre-docops-backup"
    cp "${HOOKS_DIR}/${name}" "$backup"
    echo "Backed up existing ${name} hook to ${backup}"
  fi
  cp "${SOURCE_DIR}/${name}" "${HOOKS_DIR}/${name}"
  chmod +x "${HOOKS_DIR}/${name}"
  echo "Installed ${HOOKS_DIR}/${name}"
done

echo "OK: DocOps Protocol git hooks installed and active."
exit 0
