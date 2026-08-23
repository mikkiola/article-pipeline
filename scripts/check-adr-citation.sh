#!/usr/bin/env bash
# Destination-invariant check: fails if a literal ADR-NNNN citation is
# found in docs/ARCHITECTURE.md, docs/ROADMAP.md, or
# docs/CONSTITUTION.md -- per docs/CONSTITUTION.md's "ADR discipline"
# section, these three describe decisions in prose without citing a
# specific ADR number. docs/BACKLOG.md is explicitly exempted (task
# log/history journal, not architectural description) -- not checked
# here, by design, not by omission.
#
# Extracted from an inline scripts/hooks/pre-push check (Metadata/ID
# Layer /spec interview, 2026-08-22), which had two bugs this rewrite
# fixes: its pattern (`00[0-9][0-9]`, a bare backtick-wrapped number)
# never matched this project's actual "ADR-NNNN" citation style, and
# its target list wrongly included docs/BACKLOG.md before BACKLOG.md's
# exemption was decided.
#
# Checks the destination file's current state directly, not how a
# citation got there (manual edit, migration from BACKLOG.md, an
# external contributor) -- same "protect the invariant, not the
# writing process" design as scripts/check-doc-pairing.sh's own
# doc-pairing check.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

target_docs="docs/ARCHITECTURE.md docs/ROADMAP.md docs/CONSTITUTION.md"

found=0
for doc in $target_docs; do
  [ -f "$doc" ] || continue
  if grep -n 'ADR-[0-9]\+' "$doc"; then
    found=1
  fi
done

if [ "$found" -eq 1 ]; then
  echo "FAIL: found ADR-number citation(s) above in a top-level doc."
  echo "docs/ARCHITECTURE.md, docs/ROADMAP.md, and docs/CONSTITUTION.md describe decisions in prose, never by ADR number -- see docs/CONSTITUTION.md's \"ADR discipline\" section."
  echo "(docs/BACKLOG.md is exempt -- it's a task log, not an architectural description.)"
  exit 1
fi

echo "OK: no ADR-number citations found in ARCHITECTURE.md/ROADMAP.md/CONSTITUTION.md."
exit 0
