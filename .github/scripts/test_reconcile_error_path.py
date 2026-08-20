#!/usr/bin/env python3
"""Case 6 of .github/scripts/test-reconcile.sh's scenario suite:
"exception mid-flow" (ToolTempest Tier 2 Stage 3, commit dca412e),
adapted for reconcile.py -- kept as a separate Python-level test rather
than a seventh case in that shell script; see below for why.

Why a monkeypatch, not a real fault (e.g. a read-only file): reconcile.py
always reads docs/ARCHITECTURE.md's own on-disk content and passes it
back to apply_tier2_sync() as `proposed` (ADR-0034 -- "the proposed
content is the merged PR's own tree ... never generated here"). That
means apply_tier2_sync()'s diff against its own snapshot of the exact
same file is always empty by construction, so the write_text() call
inside apply_tier2_sync() -- the only place a real OS-level fault
(permission denied, disk full, ...) could land -- is never actually
reached in reconcile.py's current design (the same structural fact
already recorded in docs/BACKLOG.md as making status="applied"
unreachable here). A git-scratch scenario like test-reconcile.sh's
cases 1-5 cannot exercise reconcile.py's try/except around
apply_tier2_sync() at all for that reason. Monkeypatching
apply_tier2_sync() to raise is the only way to confirm what that
try/except actually does: log a clean "error" evidence record, still
commit and push it, and exit 1 -- rather than silently losing the
record or crashing uncaught.

Isolated scratch repo + fake local origin, same method as
test-reconcile.sh -- no contact with real origin or the GitHub API.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
)

RECONCILE_PY = REPO_ROOT / ".github" / "scripts" / "reconcile.py"
DOC_SYNC_PY = REPO_ROOT / "scripts" / "doc_sync.py"
DOC_SYNC_TIER2_PY = REPO_ROOT / "scripts" / "doc_sync_tier2.py"

SEED_ARCHITECTURE = "# ARCHITECTURE\n\nSeed content.\n"


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    for p in (RECONCILE_PY, DOC_SYNC_PY, DOC_SYNC_TIER2_PY):
        if not p.is_file():
            return fail(f"{p} not found (run scripts/sync-tooling.sh first)")

    scratch = Path(tempfile.mkdtemp())
    try:
        origin = scratch / "origin.git"
        work = scratch / "work"
        run(["git", "init", "--bare", "-q", str(origin)])
        run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=origin)
        run(["git", "clone", "-q", str(origin), str(work)])
        run(["git", "config", "user.email", "test@test.local"], cwd=work)
        run(["git", "config", "user.name", "test"], cwd=work)
        (work / "scripts").mkdir(parents=True, exist_ok=True)
        (work / "docs").mkdir(parents=True, exist_ok=True)
        shutil.copy(DOC_SYNC_PY, work / "scripts" / "doc_sync.py")
        shutil.copy(DOC_SYNC_TIER2_PY, work / "scripts" / "doc_sync_tier2.py")
        (work / "docs" / "ARCHITECTURE.md").write_text(SEED_ARCHITECTURE, encoding="utf-8")
        run(["git", "add", "-A"], cwd=work)
        run(["git", "commit", "-q", "-m", "seed"], cwd=work)
        run(["git", "push", "-q", "origin", "HEAD:main"], cwd=work)
        merged_sha = run(["git", "rev-parse", "HEAD"], cwd=work).stdout.strip()

        old_cwd = os.getcwd()
        old_sys_path = list(sys.path)
        for name in ("doc_sync", "doc_sync_tier2", "reconcile"):
            sys.modules.pop(name, None)
        os.chdir(work)
        try:
            spec = importlib.util.spec_from_file_location("reconcile", RECONCILE_PY)
            reconcile = importlib.util.module_from_spec(spec)
            sys.modules["reconcile"] = reconcile
            spec.loader.exec_module(reconcile)  # REPO_ROOT resolves via cwd=work

            captured_stdout = io.StringIO()
            with mock.patch.object(
                reconcile, "apply_tier2_sync",
                side_effect=RuntimeError("simulated mid-flow failure"),
            ), mock.patch.dict(os.environ, {"PR_NUMBER": "401", "MERGED_SHA": merged_sha}):
                with contextlib.redirect_stdout(captured_stdout):
                    exit_code = reconcile.main()
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_sys_path

        stdout_text = captured_stdout.getvalue()
        print(stdout_text, end="")  # keep reconcile.py's own output visible

        if exit_code != 1:
            return fail(f"exit code was {exit_code}, expected 1 (error path)")

        runs_dir = work / ".tempest" / "runs"
        records = sorted(runs_dir.glob("docops_*.json"))
        if len(records) != 1:
            return fail(f"expected exactly 1 evidence record, found {len(records)}")
        record = json.loads(records[0].read_text(encoding="utf-8"))
        if record["status"] != "error":
            return fail(f"evidence record status was {record['status']!r}, expected 'error'")
        if "simulated mid-flow failure" not in (record.get("error") or ""):
            return fail(f"evidence record error field did not capture the exception: {record.get('error')!r}")

        log = run(["git", "log", "-1", "--pretty=%s"], cwd=work).stdout.strip()
        if "(error)" not in log:
            return fail(f"commit message did not record the error outcome: {log!r}")

        origin_log = subprocess.run(
            ["git", "--git-dir", str(origin), "log", "main", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, check=True,
        ).stdout
        if ".tempest/runs" not in origin_log:
            return fail("evidence record for the error run was not pushed to origin")

        arch_text = (work / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        if arch_text != SEED_ARCHITECTURE:
            return fail("docs/ARCHITECTURE.md was modified despite the simulated failure")

        if "[reconcile] status=error written=" not in stdout_text:
            return fail(
                "printed status line did not say status=error on a genuine "
                f"failure (result.get('status') stayed at its no_changes "
                f"placeholder instead): {stdout_text!r}"
            )

        print("OK: case 6 (exception mid-flow) -- clean 'error' evidence record, committed and pushed, exit 1.")
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
