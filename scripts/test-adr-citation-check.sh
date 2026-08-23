#!/usr/bin/env bash
# Regression test for scripts/check-adr-citation.sh (Metadata/ID Layer
# /spec interview, 2026-08-22): confirms the destination-invariant
# ADR-citation check hard-blocks a literal ADR-NNNN citation in
# ARCHITECTURE.md/ROADMAP.md/CONSTITUTION.md, stays silent when
# BACKLOG.md carries the same citation (explicitly exempted), and
# passes clean docs with zero citations anywhere.
#
# Mutation-testing precedent for this exact check: BACKLOG.md's own
# [B-019] entry records that the check's PRIOR pattern
# (backtick-wrapped bare number) was confirmed to actually block a
# push on 2026-08-15. This test targets the FIXED check
# (docs/BACKLOG.md's own [B-034] finding: the old pattern never
# matched real ADR-NNNN citations at all) and additionally confirms
# BACKLOG.md's new exemption.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_SCRIPT="${REPO_ROOT}/scripts/check-adr-citation.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$CHECK_SCRIPT" ] || fail "${CHECK_SCRIPT} not found"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

mkdir -p "${SCRATCH}/docs"
seed_clean() {
  echo "# Architecture" > "${SCRATCH}/docs/ARCHITECTURE.md"
  echo "# Roadmap" > "${SCRATCH}/docs/ROADMAP.md"
  echo "# Constitution" > "${SCRATCH}/docs/CONSTITUTION.md"
  echo "# Backlog" > "${SCRATCH}/docs/BACKLOG.md"
}

run_check() {
  (cd "$SCRATCH" && bash "$CHECK_SCRIPT")
}

# Case A: clean docs, zero citations anywhere -- expect pass (exit 0).
seed_clean
OUT_A="$(run_check)"; EXIT_A=$?
[ "$EXIT_A" -eq 0 ] || fail "case A: exit code was $EXIT_A, expected 0 (clean docs)"

# Case B: ARCHITECTURE.md cites ADR-0031 -- expect block (exit 1).
seed_clean
echo "See ADR-0031 for the resolved question." >> "${SCRATCH}/docs/ARCHITECTURE.md"
EXIT_B=0; OUT_B="$(run_check)" || EXIT_B=$?
[ "$EXIT_B" -eq 1 ] || fail "case B: exit code was $EXIT_B, expected 1 (ARCHITECTURE.md citation)"

# Case C: ROADMAP.md cites ADR-0031 -- expect block (exit 1).
seed_clean
echo "Resolved per ADR-0031." >> "${SCRATCH}/docs/ROADMAP.md"
EXIT_C=0; OUT_C="$(run_check)" || EXIT_C=$?
[ "$EXIT_C" -eq 1 ] || fail "case C: exit code was $EXIT_C, expected 1 (ROADMAP.md citation)"

# Case D: CONSTITUTION.md cites ADR-0031 -- expect block (exit 1).
seed_clean
echo "See ADR-0031." >> "${SCRATCH}/docs/CONSTITUTION.md"
EXIT_D=0; OUT_D="$(run_check)" || EXIT_D=$?
[ "$EXIT_D" -eq 1 ] || fail "case D: exit code was $EXIT_D, expected 1 (CONSTITUTION.md citation)"

# Case E: BACKLOG.md cites ADR-0031, the other three stay clean --
# expect pass (exit 0). This is the explicit exemption.
seed_clean
echo "Closed via ADR-0031." >> "${SCRATCH}/docs/BACKLOG.md"
OUT_E="$(run_check)"; EXIT_E=$?
[ "$EXIT_E" -eq 0 ] || fail "case E: exit code was $EXIT_E, expected 0 (BACKLOG.md is exempt)"

# Case F: the check must actually match the real citation style used
# throughout this project (plain "ADR-0031", no backticks) -- this is
# the exact pattern the check's PRIOR version silently failed to
# match. Confirms the fix, not just the new script's existence.
seed_clean
echo "ADR-0039" >> "${SCRATCH}/docs/ARCHITECTURE.md"
EXIT_F=0; OUT_F="$(run_check)" || EXIT_F=$?
[ "$EXIT_F" -eq 1 ] || fail "case F: exit code was $EXIT_F, expected 1 (plain ADR-NNNN, no backticks, must match)"

echo "OK: clean docs pass; ARCHITECTURE.md/ROADMAP.md/CONSTITUTION.md each independently block on an ADR-NNNN citation; BACKLOG.md is exempt; plain (non-backtick-wrapped) ADR-NNNN citations are correctly matched."
exit 0
