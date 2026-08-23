#!/usr/bin/env bash
# Regression test for scripts/generate_adr_index.py (Metadata/ID Layer
# /spec interview, 2026-08-22, Step 6): confirms the generator reads
# id/status/supersedes/superseded_by from frontmatter and each file's
# H1 title correctly, for a small scratch fixture (not the real 40).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GEN_SCRIPT="${REPO_ROOT}/scripts/generate_adr_index.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$GEN_SCRIPT" ] || fail "${GEN_SCRIPT} not found"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

mkdir -p "${SCRATCH}/docs/adr"

cat > "${SCRATCH}/docs/adr/0001-first-decision.md" <<'EOF'
---
id: ADR-0001
status: Superseded
supersedes: null
superseded_by: ADR-0002
source_type: verbatim
---

# 0001 — First Decision

## Status

Superseded by 0002.
EOF

cat > "${SCRATCH}/docs/adr/0002-second-decision.md" <<'EOF'
---
id: ADR-0002
status: Accepted
supersedes: ADR-0001
superseded_by: null
source_type: inferred
---

# ADR-0002: Second Decision

## Status

Accepted
EOF

cd "$SCRATCH" && python3 "$GEN_SCRIPT"
EXIT_CODE=$?
[ "$EXIT_CODE" -eq 0 ] || fail "generator exited $EXIT_CODE, expected 0"

INDEX="${SCRATCH}/docs/adr/ADR-INDEX.md"
[ -f "$INDEX" ] || fail "ADR-INDEX.md was not created"

OUT="$(cat "$INDEX")"

echo "$OUT" | grep -q "ADR-0001" || fail "index missing ADR-0001"
echo "$OUT" | grep -q "First Decision" || fail "index missing ADR-0001's title"
echo "$OUT" | grep -q "Superseded" || fail "index missing ADR-0001's status"
echo "$OUT" | grep -q "ADR-0002" || fail "index missing ADR-0002"
echo "$OUT" | grep -q "Second Decision" || fail "index missing ADR-0002's title"

# ADR-0001's row must show its own superseded_by (ADR-0002), and
# ADR-0002's row must show its own supersedes (ADR-0001) -- confirms
# both directions of the field pair are read correctly, not just one.
ROW_0001="$(echo "$OUT" | grep "0001-first-decision.md")"
ROW_0002="$(echo "$OUT" | grep "0002-second-decision.md")"
echo "$ROW_0001" | grep -q "ADR-0002" || fail "ADR-0001's row doesn't show superseded_by: ADR-0002"
echo "$ROW_0002" | grep -q "ADR-0001" || fail "ADR-0002's row doesn't show supersedes: ADR-0001"

echo "OK: generator reads id/status/supersedes/superseded_by from frontmatter and each file's title correctly."
exit 0
