#!/usr/bin/env bash
# Regression test for scripts/check-doc-pairing.sh (DocOps SPEC.md M2,
# 2026-08-21): confirms a component-directory change independently
# warns about each of ARCHITECTURE.md/BACKLOG.md/ROADMAP.md/README.md
# that wasn't updated in the same push, stays silent about any that
# were, and never sets a failing exit code (warning-only is unchanged
# by this extension -- severity is a separate, still-open decision).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_SCRIPT="${REPO_ROOT}/scripts/check-doc-pairing.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$CHECK_SCRIPT" ] || fail "${CHECK_SCRIPT} not found"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

git init --bare -q "${SCRATCH}/origin.git"
git -C "${SCRATCH}/origin.git" symbolic-ref HEAD refs/heads/main

WORK="${SCRATCH}/work"
git clone -q "${SCRATCH}/origin.git" "$WORK"
cd "$WORK"
git config user.email test@test.local
git config user.name test

mkdir -p claim_extraction docs
echo "seed" > claim_extraction/seed.py
echo "# ARCHITECTURE" > docs/ARCHITECTURE.md
echo "# BACKLOG" > docs/BACKLOG.md
echo "# ROADMAP" > docs/ROADMAP.md
echo "# README" > README.md
git add -A
git commit -q -m "seed"
git push -q origin HEAD:main
git branch -q --set-upstream-to=origin/main main
SEED_SHA="$(git rev-parse HEAD)"

check_warns_for() {
  # $1 = expected doc substring, $2 = output
  echo "$2" | grep -q "$1 was NOT updated"
}

# Case A: component change, no doc updates -- expect all four warnings.
echo "modified" >> claim_extraction/seed.py
git add -A && git commit -q -m "case A: no doc updates"
OUT_A="$(bash "$CHECK_SCRIPT")"
EXIT_A=$?
[ "$EXIT_A" -eq 0 ] || fail "case A: exit code was $EXIT_A, expected 0 (warning-only)"
for doc in "docs/ARCHITECTURE.md" "docs/BACKLOG.md" "docs/ROADMAP.md" "README.md"; do
  check_warns_for "$doc" "$OUT_A" || fail "case A: expected a warning for $doc, got none"
done

# Case B: component change, ARCHITECTURE.md updated only -- expect
# warnings for the other three, silence on ARCHITECTURE.md.
git reset -q --hard "$SEED_SHA"
echo "modified" >> claim_extraction/seed.py
echo "updated" >> docs/ARCHITECTURE.md
git add -A && git commit -q -m "case B: ARCHITECTURE.md updated only"
OUT_B="$(bash "$CHECK_SCRIPT")"
EXIT_B=$?
[ "$EXIT_B" -eq 0 ] || fail "case B: exit code was $EXIT_B, expected 0 (warning-only)"
if check_warns_for "docs/ARCHITECTURE.md" "$OUT_B"; then
  fail "case B: ARCHITECTURE.md was updated but still got a warning"
fi
for doc in "docs/BACKLOG.md" "docs/ROADMAP.md" "README.md"; do
  check_warns_for "$doc" "$OUT_B" || fail "case B: expected a warning for $doc, got none"
done

# Case C: component change, all four docs updated -- expect no warnings.
git reset -q --hard "$SEED_SHA"
echo "modified" >> claim_extraction/seed.py
echo "updated" >> docs/ARCHITECTURE.md
echo "updated" >> docs/BACKLOG.md
echo "updated" >> docs/ROADMAP.md
echo "updated" >> README.md
git add -A && git commit -q -m "case C: all four docs updated"
OUT_C="$(bash "$CHECK_SCRIPT")"
EXIT_C=$?
[ "$EXIT_C" -eq 0 ] || fail "case C: exit code was $EXIT_C, expected 0"
if echo "$OUT_C" | grep -q "WARNING:"; then
  fail "case C: all four docs were updated but a warning was still produced: $OUT_C"
fi

# Case D: no component-directory change at all -- expect no warnings,
# regardless of doc state.
git reset -q --hard "$SEED_SHA"
echo "unrelated" >> README.md
git add -A && git commit -q -m "case D: no component change"
OUT_D="$(bash "$CHECK_SCRIPT")"
EXIT_D=$?
[ "$EXIT_D" -eq 0 ] || fail "case D: exit code was $EXIT_D, expected 0"
if echo "$OUT_D" | grep -q "WARNING:"; then
  fail "case D: no component directory changed but a warning was still produced: $OUT_D"
fi

echo "OK: case A (no docs updated) warns for all four; case B (partial) warns for exactly the three missing; case C (all updated) and case D (no component change) produce no warnings; exit code stays 0 throughout."
exit 0
