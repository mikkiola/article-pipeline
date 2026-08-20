#!/usr/bin/env bash
# Regression test for the "local-fs-path" gitleaks rule in .gitleaks.toml
# (ADR-0038, extends ADR-0018's territory): confirms the rule catches a
# local machine filesystem path (macOS /Users/<user>/... or Linux
# /home/<user>/...) while leaving GitHub/GitLab usernames, repo
# references, and a URL that merely contains "/home/" as a path segment
# alone. Also re-checks the real repo's current tree stays clean --
# adding this rule must not retroactively flag anything already present
# (gitleaks' --no-git scan reads the raw filesystem, not git's index, so
# it doesn't respect .gitignore; three gitignored local-config files
# would have false-positived here without the allowlist this test also
# guards).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOML_FILE="${REPO_ROOT}/.gitleaks.toml"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$TOML_FILE" ] || fail "${TOML_FILE} not found"
command -v gitleaks >/dev/null 2>&1 || fail "gitleaks not installed"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

cp "$TOML_FILE" "${SCRATCH}/.gitleaks.toml"

# Should flag: real local filesystem paths.
cat > "${SCRATCH}/should_flag_macos.txt" <<'EOF'
detail: /Users/testuser/Dev/project/private-notes/file.md
EOF
cat > "${SCRATCH}/should_flag_linux.txt" <<'EOF'
path: /home/someuser/projects/secret-notes/file.md
EOF

# Should NOT flag: bare GitHub/GitLab usernames and repo references (the
# owner's intentional, public portfolio identity), and a URL that
# happens to contain "/home/" as an ordinary path segment.
cat > "${SCRATCH}/should_not_flag.txt" <<'EOF'
repo: lyolich777ka/brain.git
owner: mikkiola
url: https://example.com/home/index.html
EOF

REPORT="${SCRATCH}/report.json"
( cd "$SCRATCH" && gitleaks detect --source . --no-git --report-format json --report-path "$REPORT" >/dev/null 2>&1 ) || true
[ -f "$REPORT" ] || fail "gitleaks did not produce a report at ${REPORT}"

FLAGGED_FILES="$(python3 -c "
import json
with open('${REPORT}') as f:
    findings = json.load(f)
files = sorted({f['File'] for f in findings if f.get('RuleID') == 'local-fs-path'})
print('\n'.join(files))
")"

echo "$FLAGGED_FILES" | grep -qx "should_flag_macos.txt" \
  || fail "should_flag_macos.txt was NOT flagged by local-fs-path (expected it to be)"
echo "$FLAGGED_FILES" | grep -qx "should_flag_linux.txt" \
  || fail "should_flag_linux.txt was NOT flagged by local-fs-path (expected it to be)"
if echo "$FLAGGED_FILES" | grep -qx "should_not_flag.txt"; then
  fail "should_not_flag.txt WAS flagged by local-fs-path (bare usernames/URL must not trigger it)"
fi

echo "OK: local-fs-path rule flags real local paths, ignores bare usernames/URLs."

# Confirm the real repo's current tree stays clean with this rule active
# -- must not retroactively flag anything already present. Invoked the
# same way the production pre-push hook does (relative "." source, cwd
# = repo root) -- an absolute --source path would report absolute
# findings paths, which wouldn't match the allowlist's relative-path
# regexes and would produce a false failure here, not a real one.
if ! ( cd "$REPO_ROOT" && gitleaks detect --source . --no-git >/dev/null 2>&1 ); then
  fail "real repo state is no longer clean with the local-fs-path rule active -- re-run 'gitleaks detect --source . --no-git -v' from the repo root to see what's flagged"
fi

echo "OK: real repo tree stays clean with the local-fs-path rule active."
exit 0
