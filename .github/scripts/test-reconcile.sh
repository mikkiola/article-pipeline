#!/usr/bin/env bash
# Regression test for .github/scripts/reconcile.py + the `reconcile` job
# in .github/workflows/adr-0033-reconciliation.yml (ADR-0033 point 1,
# narrowed by ADR-0034/ADR-0035). Isolated scratch repo, fake local
# `origin`, no contact with real origin or the GitHub API -- same
# method as scripts/test-doc-pairing-check.sh and the uncommitted M3
# concurrent-push-race scratch test this formalizes (docs/BACKLOG.md,
# SPEC.md M3).
#
# Scenario mapping to ToolTempest's Tier 2 Stage 3 six-scenario list
# (tooltempest commit dca412e: "Verified against six scenarios:
# accept-all, atomic rollback, dirty pre-invocation state, constrained
# non-interactive mode, invalid input as rejection, exception
# mid-flow"), adapted to GitHub events and narrowed by ADR-0035 (no
# reconciliation PR, no rollback job, no gated-doc writes -- reconcile.py
# only ever touches docs/ARCHITECTURE.md, always interactive=False):
#
#   accept-all                  -> Case 1 (clean apply via a merge --
#                                  the common no_changes path)
#   dirty pre-invocation state  -> Case 2 (docs/ARCHITECTURE.md absent
#                                  at reconciliation time)
#   constrained non-interactive -> Case 3 (static: reconcile.py's
#                                  `proposed` dict can never contain a
#                                  GATED_DOCS key, by construction --
#                                  there is no code path that reads
#                                  BACKLOG.md/ROADMAP.md into it)
#   atomic rollback              -> N/A. ADR-0035 removed the only
#                                  mutation (BACKLOG.md/ROADMAP.md) this
#                                  scenario rolled back. reconcile.py's
#                                  own ARCHITECTURE.md write has no
#                                  rollback path at all -- a failure
#                                  inside apply_tier2_sync() just logs an
#                                  "error" evidence record and exits 1
#                                  (see test_reconcile_error_path.py).
#                                  Nothing exists here to roll back.
#   invalid input as rejection   -> N/A. reconcile.py always calls
#                                  apply_tier2_sync(interactive=False);
#                                  no input() prompt exists in this
#                                  workflow to reject.
#   exception mid-flow           -> Covered separately, at the Python
#                                  level, in test_reconcile_error_path.py
#                                  (see that file's header for why: the
#                                  proposed content reconcile.py builds
#                                  is always byte-identical to what's
#                                  already on disk, so a *real* content
#                                  difference -- and thus a write_text()
#                                  call inside apply_tier2_sync() an OS-
#                                  level fault could hit -- is
#                                  structurally unreachable here; a
#                                  git-level scratch scenario cannot
#                                  exercise this path at all).
#
# Plus ADR-0033 point 5 / Validation section's "close-and-reopen path
# under a simulated concurrent merge": confirmed moot as originally
# specified (docs/BACKLOG.md -- "no reconciliation PR exists anywhere
# in the ADR-0035-narrowed design"). Reformalized here as Case 4/5: a
# permanent, committed regression test of the concurrency hazard found
# in its place -- a git push race between two reconciliation runs --
# whose fix (push_with_retry()) was previously verified only by an
# uncommitted scratch test (SPEC.md M3).
#
# NOT covered here: the `pull_request.closed` / `merged != true` guard
# that keeps this job from running at all on a closed-without-merge PR.
# That guard is the job-level `if:` in adr-0033-reconciliation.yml, not
# application logic in reconcile.py -- it cannot be exercised by
# invoking the script directly, only by GitHub's own Actions runtime.
# Verified by reading the workflow file instead (see the task report).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RECONCILE_PY="${REPO_ROOT}/.github/scripts/reconcile.py"
DOC_SYNC_PY="${REPO_ROOT}/scripts/doc_sync.py"
DOC_SYNC_TIER2_PY="${REPO_ROOT}/scripts/doc_sync_tier2.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$RECONCILE_PY" ] || fail "${RECONCILE_PY} not found"
[ -f "$DOC_SYNC_PY" ] || fail "${DOC_SYNC_PY} not found (run scripts/sync-tooling.sh first)"
[ -f "$DOC_SYNC_TIER2_PY" ] || fail "${DOC_SYNC_TIER2_PY} not found (run scripts/sync-tooling.sh first)"

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

# Seeds a bare "origin" plus one work clone with the minimal repo shape
# reconcile.py needs: vendored scripts/doc_sync.py + doc_sync_tier2.py
# (normally installed by scripts/sync-tooling.sh; copied directly here
# since that script talks to the real ToolTempest remote) and, unless
# $1 = "no-arch", docs/ARCHITECTURE.md.
seed_repo() {
  local name="$1" include_arch="$2"
  local origin="${SCRATCH}/${name}-origin.git"
  local work="${SCRATCH}/${name}-work"
  git init --bare -q "$origin"
  git -C "$origin" symbolic-ref HEAD refs/heads/main
  git clone -q "$origin" "$work"
  (
    cd "$work"
    git config user.email test@test.local
    git config user.name test
    mkdir -p scripts docs
    cp "$DOC_SYNC_PY" scripts/doc_sync.py
    cp "$DOC_SYNC_TIER2_PY" scripts/doc_sync_tier2.py
    if [ "$include_arch" = "with-arch" ]; then
      printf '# ARCHITECTURE\n\nSeed content.\n' > docs/ARCHITECTURE.md
    fi
    git add -A
    git commit -q -m "seed"
    git push -q origin HEAD:main
  )
  echo "$work"
}

run_reconcile() {
  # $1 = work dir, $2 = PR_NUMBER, $3 = MERGED_SHA
  (
    cd "$1"
    PR_NUMBER="$2" MERGED_SHA="$3" python3 "$RECONCILE_PY"
  )
}

# --- Case 1: accept-all / clean apply via a merge (the common case).
# docs/ARCHITECTURE.md is present and reconcile.py's own proposed
# content is read from that same on-disk file, so apply_tier2_sync()'s
# diff is always empty by construction -- status must be "no_changes",
# never "applied" (a previously-recorded finding, docs/BACKLOG.md).
# The run must still succeed: an evidence record is new every time.
WORK1="$(seed_repo case1 with-arch)"
EXIT1=0
OUT1="$(run_reconcile "$WORK1" "101" "$(git -C "$WORK1" rev-parse HEAD)")" || EXIT1=$?
[ "$EXIT1" -eq 0 ] || fail "case 1: exit code was $EXIT1, expected 0"
echo "$OUT1" | grep -q 'status=no_changes' || fail "case 1: expected status=no_changes, got: $OUT1"
echo "$OUT1" | grep -q 'error=None' || fail "case 1: expected error=None, got: $OUT1"
RECORD1="$(git -C "$WORK1" show --stat -1 --pretty=format: | grep -c '.tempest/runs/.*\.json' || true)"
[ "$RECORD1" -eq 1 ] || fail "case 1: expected exactly one new evidence record committed, found $RECORD1"
git -C "$WORK1" log -1 --pretty=%s | grep -q "PR #101 (no_changes)" || fail "case 1: commit message missing PR number/outcome"

# --- Case 2: dirty pre-invocation state -- docs/ARCHITECTURE.md absent
# at reconciliation time (e.g. removed by a later commit on main before
# this PR's reconciliation runs). reconcile.py's own contract: proposed
# stays empty, apply_tier2_sync() leaves the (nonexistent) file
# untouched -- must not crash, must still log+push a no_changes record.
WORK2="$(seed_repo case2 no-arch)"
EXIT2=0
OUT2="$(run_reconcile "$WORK2" "102" "$(git -C "$WORK2" rev-parse HEAD)")" || EXIT2=$?
[ "$EXIT2" -eq 0 ] || fail "case 2: exit code was $EXIT2, expected 0"
echo "$OUT2" | grep -q 'status=no_changes' || fail "case 2: expected status=no_changes, got: $OUT2"
[ -f "${WORK2}/docs/ARCHITECTURE.md" ] && fail "case 2: docs/ARCHITECTURE.md should still be absent, apply_tier2_sync must not create it"

# --- Case 3: constrained non-interactive mode, by construction.
# reconcile.py's `proposed` dict -- the only input apply_tier2_sync()
# ever sees -- must be assigned exactly once, and only under the
# ARCHITECTURE_MD key; there must be no live code path that could ever
# populate a GATED_DOCS key (docs/BACKLOG.md, docs/ROADMAP.md). Checked
# by static inspection of actual assignments (`proposed[...] = `), not a
# runtime scenario, since the prose in this file's own module docstring
# mentions both gated paths by name while explaining why they're never
# touched -- a plain text grep for the path strings would false-positive
# on that docstring. (apply_tier2_sync()'s own runtime RuntimeError
# enforcement of this constraint is ToolTempest's, already covered by
# its own Stage 3 suite, not re-tested here.)
ASSIGNMENTS="$(grep -c 'proposed\[' "$RECONCILE_PY")"
[ "$ASSIGNMENTS" -eq 1 ] || fail "case 3: expected exactly 1 assignment into proposed[...], found $ASSIGNMENTS -- re-audit for a new gated-doc write path"
grep -q 'proposed\[ARCHITECTURE_MD\]' "$RECONCILE_PY" || fail "case 3: the one proposed[...] assignment is not keyed by ARCHITECTURE_MD"

# --- Case 4: concurrent push race (formalizes SPEC.md M3's uncommitted
# scratch test). Two reconciliation runs against clones of the same
# origin; the second's local HEAD is stale by the time it tries to
# push. push_with_retry() must fetch+rebase and succeed -- both
# evidence records must land on origin, in some order, neither lost.
ORIGIN4="${SCRATCH}/case4-origin.git"
git init --bare -q "$ORIGIN4"
git -C "$ORIGIN4" symbolic-ref HEAD refs/heads/main
WORK4A="${SCRATCH}/case4-work-a"
WORK4B="${SCRATCH}/case4-work-b"
git clone -q "$ORIGIN4" "$WORK4A"
for w in "$WORK4A"; do
  ( cd "$w"
    git config user.email test@test.local; git config user.name test
    mkdir -p scripts docs
    cp "$DOC_SYNC_PY" scripts/doc_sync.py
    cp "$DOC_SYNC_TIER2_PY" scripts/doc_sync_tier2.py
    printf '# ARCHITECTURE\n\nSeed content.\n' > docs/ARCHITECTURE.md
    git add -A && git commit -q -m seed && git push -q origin HEAD:main )
done
git clone -q "$ORIGIN4" "$WORK4B"
SHA4="$(git -C "$WORK4A" rev-parse HEAD)"
# A runs first and pushes its evidence-record commit immediately.
EXIT4A=0
run_reconcile "$WORK4A" "201" "$SHA4" > /dev/null || EXIT4A=$?
[ "$EXIT4A" -eq 0 ] || fail "case 4: run A exit code was $EXIT4A, expected 0"
# B is still on the pre-A local HEAD -- its push must be rejected once,
# then retried via fetch+rebase.
EXIT4B=0
OUT4B="$(run_reconcile "$WORK4B" "202" "$SHA4")" || EXIT4B=$?
[ "$EXIT4B" -eq 0 ] || fail "case 4: run B exit code was $EXIT4B, expected 0 (retry should succeed)"
RECORDS_ON_ORIGIN="$(git --git-dir="$ORIGIN4" log main --name-only --pretty=format: | grep -c '\.tempest/runs/.*\.json' || true)"
[ "$RECORDS_ON_ORIGIN" -eq 2 ] || fail "case 4: expected 2 evidence records on origin main, found $RECORDS_ON_ORIGIN"

# --- Case 5: permanent push failure -- origin genuinely unreachable
# for the entire retry window (not just transiently stale). Must fail
# cleanly (logged "[reconcile] FAIL: ...", exit 1), not crash with an
# uncaught traceback.
WORK5="$(seed_repo case5 with-arch)"
BROKEN_ORIGIN="$(git -C "$WORK5" remote get-url origin)"
rm -rf "$BROKEN_ORIGIN"
EXIT5=0
OUT5="$(run_reconcile "$WORK5" "301" "$(git -C "$WORK5" rev-parse HEAD)" 2>&1)" || EXIT5=$?
[ "$EXIT5" -eq 1 ] || fail "case 5: exit code was $EXIT5, expected 1 (clean failure)"
echo "$OUT5" | grep -q '\[reconcile\] FAIL:' || fail "case 5: expected a clean '[reconcile] FAIL: ...' message, got: $OUT5"
echo "$OUT5" | grep -qi 'Traceback' && fail "case 5: got an uncaught traceback instead of a clean failure"

echo "OK: all reconcile.py scenarios passed (cases 1-5; case 6 in test_reconcile_error_path.py)."
