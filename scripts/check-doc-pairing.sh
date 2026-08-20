#!/usr/bin/env bash
# Warns (never blocks) when a component-directory change isn't paired
# with an update to one of the Tier 2 docs in the same push. Originally
# inline in scripts/hooks/pre-push, ARCHITECTURE.md-only; extracted
# into its own script and extended to also cover BACKLOG.md,
# ROADMAP.md, and README.md, per DocOps SPEC.md's M2 milestone
# (2026-08-21). Article-pipeline-specific by design (the component
# directory list below is this project's own, not a generic
# ToolTempest mechanism -- see ToolTempest's own README on this
# boundary: "each consumer that wants it has to replicate the pattern
# into its own pre-push hook independently").
#
# Severity is deliberately unchanged: this remains warning-only, never
# sets a failing exit code. Whether it should become hard-fail is a
# separate, still-open docs/BACKLOG.md "Owner decisions needed" item,
# not re-decided by this extension -- this script only widens which
# docs are checked, not what happens when one is missing.
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
