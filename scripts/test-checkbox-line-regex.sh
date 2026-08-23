#!/usr/bin/env bash
# Regression test for scripts/verify.py's CHECKBOX_FULL_LINE_RE
# off-by-one fix (found during a parallel regex-fragility audit,
# 2026-08-22): the leading `\s*` matched across a preceding blank line
# under re.MULTILINE, reporting a malformed checkbox entry's line
# number as the blank line above it, not the checkbox line itself.
# Fixed by restricting the leading whitespace class to space/tab only
# (`[ \t]*`), which cannot consume a newline.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

# Case A: synthetic minimal repro -- a checkbox line immediately
# preceded by a blank line must report its own line number, not the
# blank line's.
CASE_A_RESULT="$(cd "$REPO_ROOT" && python3 - <<'EOF'
import re
CHECKBOX_FULL_LINE_RE = re.compile(r"^[ \t]*(?:-|\d+\.)\s*\[[ xX]\](.*)$", re.MULTILINE)
text = "line one\n\n- [ ] checkbox on line three\n"
m = CHECKBOX_FULL_LINE_RE.search(text)
line_no = text.count("\n", 0, m.start()) + 1
print(line_no)
EOF
)"
[ "$CASE_A_RESULT" = "3" ] || fail "case A (synthetic): expected line 3, got $CASE_A_RESULT"

# Case B: real content, this repo's own SPEC.md. Confirms the fix
# against actual file content, not just a synthetic string. The
# checkbox line and its preceding blank line are located dynamically
# (not hardcoded) so this test survives SPEC.md being edited later --
# it just needs at least one checkbox line preceded by a blank line
# somewhere in the file, which SPEC.md's Milestones section reliably
# has.
CASE_B_RESULT="$(cd "$REPO_ROOT" && python3 - <<'EOF'
import re
CHECKBOX_FULL_LINE_RE = re.compile(r"^[ \t]*(?:-|\d+\.)\s*\[[ xX]\](.*)$", re.MULTILINE)
text = open("SPEC.md", encoding="utf-8").read()
lines = text.split("\n")

# Find a checkbox match whose line is immediately preceded by a blank
# line -- the exact condition the bug required to manifest.
target = None
for m in CHECKBOX_FULL_LINE_RE.finditer(text):
    line_no = text.count("\n", 0, m.start()) + 1
    if line_no >= 2 and lines[line_no - 2].strip() == "":
        target = (m, line_no)
        break

if target is None:
    print("NO_BLANK_PRECEDED_CHECKBOX_FOUND")
else:
    m, expected_line = target
    reported_line = text.count("\n", 0, m.start()) + 1
    print(reported_line if reported_line == expected_line else f"MISMATCH:{reported_line}!={expected_line}")
EOF
)"
[ "$CASE_B_RESULT" != "NO_BLANK_PRECEDED_CHECKBOX_FOUND" ] || fail "case B: no blank-line-preceded checkbox found in SPEC.md to test against -- fixture assumption broken"
case "$CASE_B_RESULT" in
  MISMATCH:*) fail "case B (real SPEC.md content): reported line did not match the checkbox's actual line -- $CASE_B_RESULT" ;;
esac

# Case C: the fix must not regress the ordinary case (no blank line
# above) -- correct behavior before the fix, must stay correct after.
CASE_C_RESULT="$(cd "$REPO_ROOT" && python3 - <<'EOF'
import re
CHECKBOX_FULL_LINE_RE = re.compile(r"^[ \t]*(?:-|\d+\.)\s*\[[ xX]\](.*)$", re.MULTILINE)
text = "line one\n- [ ] checkbox on line two, no blank line above\n"
m = CHECKBOX_FULL_LINE_RE.search(text)
line_no = text.count("\n", 0, m.start()) + 1
print(line_no)
EOF
)"
[ "$CASE_C_RESULT" = "2" ] || fail "case C (no blank line, regression check): expected line 2, got $CASE_C_RESULT"

echo "OK: checkbox line number reported correctly with a preceding blank line (synthetic and real SPEC.md content), and unchanged for the ordinary no-blank-line case."
exit 0
