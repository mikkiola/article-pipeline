#!/usr/bin/env bash
# Warns (never blocks) when a push changes a component directory. For each
# of docs/ARCHITECTURE.md, docs/BACKLOG.md, docs/ROADMAP.md and README.md
# that the same push does not update, it prints a separate warning; a doc
# the push does update gets none. A push that changes no component
# directory, or a branch with no upstream, is not checked. The component
# directory list below is this project's own, not a generic ToolTempest
# mechanism.
#
# A missing doc update produces a warning only and does not fail the push.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

component_dirs="claim_extraction evidence_package strategy_layer author quality_gate platform_adapter experiment_log"
target_docs="docs/ARCHITECTURE.md docs/BACKLOG.md docs/ROADMAP.md README.md"

echo "[pre-push] Checking whether component-directory changes are paired with doc updates (ARCHITECTURE.md, BACKLOG.md, ROADMAP.md, README.md)..."

if ! git rev-parse @{u} >/dev/null 2>&1; then
  echo "[pre-push] No upstream branch to diff against yet, skipping the component/doc pairing check."
  exit 0
fi

range="$(git rev-parse @{u}).."
changed_files="$(git diff --name-only "$range" 2>/dev/null || echo "")"

changed_components=""
for d in $component_dirs; do
  if echo "$changed_files" | grep -q "^${d}/"; then
    changed_components="$changed_components $d"
  fi
done

if [ -z "$changed_components" ]; then
  exit 0
fi

for doc in $target_docs; do
  if ! echo "$changed_files" | grep -Fxq "$doc"; then
    echo "[pre-push] WARNING: these component directories changed in this push:$changed_components"
    echo "[pre-push] $doc was NOT updated in the same push."
    echo "[pre-push] If a component's Status/Validation/Commit changed, update $doc before pushing."
    echo "[pre-push] If nothing status-relevant changed (e.g. a bugfix), this warning is safe to ignore."
  fi
done

exit 0
