#!/usr/bin/env python3
"""Post-merge reconciliation: ADR-0033 point 1 (narrowed by ADR-0034's
contributor-supplied-content decision and ADR-0035's pre-merge gate for
gated docs), plus point 6 (evidence logging).

Writes docs/ARCHITECTURE.md directly via apply_tier2_sync(), per
ADR-0002(b)/ADR-0034: the proposed content is the merged PR's own
tree, already on disk in this checkout, never generated here. In the
common case this is an intentional no-op -- the contributor's ordinary
merge already wrote ARCHITECTURE.md, so apply_tier2_sync()'s own diff
against the current working tree is typically empty (ADR-0034's
Context describes this as "an effective re-write of content that
already exists on disk," not a bug). docs/BACKLOG.md/docs/ROADMAP.md
are never touched here: ADR-0035 moved their confirmation gate to
pre-merge (CODEOWNERS + branch protection), so ADR-0033 points 2/3
(reconciliation PR, rollback) are superseded and have no counterpart
in this script.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
)

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from doc_sync import make_run_id, prune_run_records  # noqa: E402
from doc_sync_tier2 import apply_tier2_sync  # noqa: E402

ARCHITECTURE_MD = "docs/ARCHITECTURE.md"


def run_git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()


def write_evidence_record(pr_number: str, merged_sha: str, result: dict, error: str | None) -> Path:
    """Writes one JSON record per run to .tempest/runs/, reusing Tier 1's
    naming/retention convention (make_run_id(), prune_run_records()) --
    not schemas/execution-record.schema.json itself, whose `hook` enum
    is pre-commit-only (Tier 1's CHECKPOINT.md/SPEC.md structural
    validation, a different domain from this post-merge reconciliation
    run). Reusing that schema verbatim isn't possible without violating
    its own additionalProperties/enum constraints; this record instead
    matches ADR-0033 point 6's fields (merged PR SHA, apply outcome),
    adapted to this workflow's narrowed, ARCHITECTURE.md-only scope --
    "rejected"/"superseded-by-reopen" outcomes no longer apply, since
    those belonged to the now-superseded reconciliation-PR flow
    (ADR-0033 points 2/3/5, see ADR-0035).
    """
    run_id = make_run_id()
    status = "error" if error is not None else result["status"]  # "applied" | "no_changes" | "error"
    record = {
        "run_id": run_id,
        "hook": "post-merge-reconciliation",
        "adr": "ADR-0033 point 1 (narrowed by ADR-0034/ADR-0035), point 6",
        "note": (
            "Not a schemas/execution-record.schema.json record -- that "
            "schema's hook enum is pre-commit-only. Reuses Tier 1's "
            "one-record-per-run convention under .tempest/runs/, not its "
            "schema."
        ),
        "pr_number": pr_number,
        "merged_commit_sha": merged_sha,
        "written": result.get("written", []) if error is None else [],
        "status": status,
        "error": error,
    }
    runs_dir = REPO_ROOT / ".tempest" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    out_path = runs_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    prune_run_records(runs_dir)
    return out_path


def main() -> int:
    pr_number = os.environ["PR_NUMBER"]
    merged_sha = os.environ["MERGED_SHA"]

    arch_path = REPO_ROOT / ARCHITECTURE_MD
    proposed: dict[str, str] = {}
    if arch_path.is_file():
        proposed[ARCHITECTURE_MD] = arch_path.read_text(encoding="utf-8")
    # If ARCHITECTURE.md is absent, proposed stays empty --
    # apply_tier2_sync() leaves a file missing from `proposed`
    # untouched, per its own contract; nothing to write.

    error: str | None = None
    result: dict = {"written": [], "status": "no_changes"}
    try:
        result = apply_tier2_sync(REPO_ROOT, proposed, interactive=False)
    except Exception as exc:  # noqa: BLE001 -- evidence log must record any failure, not swallow it silently
        error = f"{type(exc).__name__}: {exc}"

    record_path = write_evidence_record(pr_number, merged_sha, result, error)

    run_git("config", "user.name", "github-actions[bot]")
    run_git("config", "user.email", "github-actions[bot]@users.noreply.github.com")

    to_add = [str(record_path.relative_to(REPO_ROOT))]
    if ARCHITECTURE_MD in result.get("written", []):
        to_add.append(ARCHITECTURE_MD)
    run_git("add", *to_add)

    nothing_staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT).returncode == 0
    if nothing_staged:
        print("[reconcile] Nothing staged (unexpected -- the evidence record should always be new).")
        return 1 if error else 0

    run_git(
        "commit", "-m",
        f"chore(docops): post-merge reconciliation for PR #{pr_number} ({status_for_commit(result, error)})",
    )
    run_git("push", "origin", "HEAD:main")

    print(f"[reconcile] status={result.get('status')} written={result.get('written')} error={error}")
    return 1 if error else 0


def status_for_commit(result: dict, error: str | None) -> str:
    return "error" if error is not None else result.get("status", "unknown")


if __name__ == "__main__":
    sys.exit(main())
