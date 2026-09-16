#!/usr/bin/env bash
# Regression test for scripts/check-strategy-layer-boundary.sh
# (SPEC.md M6, ADR-0048's Anti-Corruption Layer boundary): confirms
# the grep-based path-hardcoding lint actually catches each of the
# four literal strings SPEC.md names ("collector/data", "daily_brief_",
# "manifest_", "claim_extraction/output") when planted in any of the
# three target files, and passes clean.
#
# Same mutation-testing discipline and scratch-repo style as
# scripts/test-adr-citation-check.sh -- confirms the check actually
# blocks a real synthetic violation, not just that the script exists
# and runs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_SCRIPT="${REPO_ROOT}/scripts/check-strategy-layer-boundary.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$CHECK_SCRIPT" ] || fail "${CHECK_SCRIPT} not found"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

mkdir -p "${SCRATCH}/strategy_layer"
seed_clean() {
  echo "def classify_unit(unit): return unit.integrity_status" > "${SCRATCH}/strategy_layer/pre_filter.py"
  echo "def build_claim_treatment(unit): return {}" > "${SCRATCH}/strategy_layer/framing.py"
  echo "def build_verdict(treatments): return {}" > "${SCRATCH}/strategy_layer/write_verdict.py"
}

run_check() {
  (cd "$SCRATCH" && bash "$CHECK_SCRIPT")
}

# Case A: clean files, no hardcoded strings anywhere -- expect pass.
seed_clean
OUT_A="$(run_check)"; EXIT_A=$?
[ "$EXIT_A" -eq 0 ] || fail "case A: exit code was $EXIT_A, expected 0 (clean files)"

# Case B: pre_filter.py hardcodes "collector/data" -- expect block.
seed_clean
echo '# path = "collector/data/manifest.json"' >> "${SCRATCH}/strategy_layer/pre_filter.py"
EXIT_B=0; OUT_B="$(run_check)" || EXIT_B=$?
[ "$EXIT_B" -eq 1 ] || fail "case B: exit code was $EXIT_B, expected 1 (pre_filter.py hardcodes collector/data)"

# Case C: framing.py hardcodes "daily_brief_" -- expect block.
seed_clean
echo '# fallback = "daily_brief_2026-09-14.json"' >> "${SCRATCH}/strategy_layer/framing.py"
EXIT_C=0; OUT_C="$(run_check)" || EXIT_C=$?
[ "$EXIT_C" -eq 1 ] || fail "case C: exit code was $EXIT_C, expected 1 (framing.py hardcodes daily_brief_)"

# Case D: write_verdict.py hardcodes "manifest_" -- expect block.
seed_clean
echo '# src = "manifest_2026-09-12.json"' >> "${SCRATCH}/strategy_layer/write_verdict.py"
EXIT_D=0; OUT_D="$(run_check)" || EXIT_D=$?
[ "$EXIT_D" -eq 1 ] || fail "case D: exit code was $EXIT_D, expected 1 (write_verdict.py hardcodes manifest_)"

# Case E: pre_filter.py hardcodes "claim_extraction/output" -- expect block.
seed_clean
echo '# legacy = "claim_extraction/output/pilot_log.json"' >> "${SCRATCH}/strategy_layer/pre_filter.py"
EXIT_E=0; OUT_E="$(run_check)" || EXIT_E=$?
[ "$EXIT_E" -eq 1 ] || fail "case E: exit code was $EXIT_E, expected 1 (pre_filter.py hardcodes claim_extraction/output)"

# Case F: a file NOT in the target list (e.g. an adapter, which is
# allowed to know its own source's paths) hardcodes "collector/data"
# -- expect pass, confirms the check is scoped to the three named
# core files only, not the whole strategy_layer/ tree.
seed_clean
mkdir -p "${SCRATCH}/strategy_layer/adapters"
echo '# path = "collector/data/manifest.json"' > "${SCRATCH}/strategy_layer/adapters/collector.py"
OUT_F="$(run_check)"; EXIT_F=$?
[ "$EXIT_F" -eq 0 ] || fail "case F: exit code was $EXIT_F, expected 0 (adapters/collector.py is out of scope by design)"

echo "OK: clean files pass; each of the four SPEC.md-named strings independently blocks when planted in pre_filter.py/framing.py/write_verdict.py; a file outside the three-file scope (e.g. an adapter) is correctly not checked."
exit 0
