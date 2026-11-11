#!/usr/bin/env bash
# Installs the DocOps Protocol git hooks (ToolTempest ADR-0001) into the
# directory where Git reads hooks for this checkout (git rev-parse
# --git-path hooks): <git-dir>/hooks in a primary clone, the shared hooks
# directory of the main repository in a linked worktree, or core.hooksPath
# when it is set. Human-triggered only -- nothing in this repository runs
# it automatically. Running it makes pre-commit run the DocOps check on the
# staged index and pre-push run the DocOps check on each pushed commit; until
# it is run, the hooks directory is left exactly as it already was.
#
# In a linked worktree the hooks directory is shared with the main repository
# and every other worktree, so running this script there also changes the
# hooks of those checkouts.
#
# Source of truth for the hook bodies is scripts/hooks/{pre-commit,
# pre-push} in this repository (tracked in git, unlike .git/hooks/
# itself). Re-run this script after pulling a change to either file to
# pick it up.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/scripts/hooks"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

git -C "${REPO_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || fail "${REPO_ROOT} is not inside a git work tree"
HOOKS_DIR="$(git -C "${REPO_ROOT}" rev-parse --git-path hooks)" \
  || fail "cannot resolve the git hooks directory"
case "${HOOKS_DIR}" in
  /*) ;;
  *) HOOKS_DIR="${REPO_ROOT}/${HOOKS_DIR}" ;;
esac
mkdir -p "${HOOKS_DIR}"
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
