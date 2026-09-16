#!/usr/bin/env bash
# Grep-based path-hardcoding lint (SPEC.md M6, ADR-0048): fails if
# strategy_layer/pre_filter.py, strategy_layer/framing.py, or
# strategy_layer/write_verdict.py contain a literal source-specific
# path/filename string -- import-linter (scripts: lint-imports,
# [tool.importlinter] in pyproject.toml) only catches real Python
# `import` statements, not a hardcoded path string embedded in a
# function body, so this closes that specific gap in the Anti-
# Corruption-Layer boundary these three files sit behind (ADR-0048).
#
# Same precedent and style as scripts/check-adr-citation.sh: a
# destination-invariant check against a fixed file list, not a
# git-diff-based check against what changed.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

target_files="strategy_layer/pre_filter.py strategy_layer/framing.py strategy_layer/write_verdict.py"

# Literal source-specific strings named in SPEC.md's M6 description.
forbidden_patterns=(
  "collector/data"
  "daily_brief_"
  "manifest_"
  "claim_extraction/output"
)

found=0
for f in $target_files; do
  [ -f "$f" ] || continue
  for pattern in "${forbidden_patterns[@]}"; do
    if grep -n -F -- "$pattern" "$f"; then
      echo "FAIL: $f contains hardcoded source-specific string '$pattern'." >&2
      found=1
    fi
  done
done

if [ "$found" -eq 1 ]; then
  echo "Strategy Layer's core files (pre_filter.py/framing.py/write_verdict.py) must stay source-agnostic -- see ADR-0048's Anti-Corruption Layer boundary." >&2
  exit 1
fi

echo "OK: no hardcoded source-specific path strings found in Strategy Layer's core files."
exit 0
