#!/usr/bin/env python3
"""Checklist -> harness mapping: execute and record, nothing more.

Step 4 of the SPEC -> checklist -> harness -> drift -> doc-sync
automation track. Reuses Step 3's checklist generation from
scripts/checklist.py (imported, not duplicated) to get each
component's VC list, then for every VC:

- verify_type == "AUTOMATED": run verify_command as a subprocess,
  capture exit code + truncated output, classify PASS/FAIL.
- verify_type == "MANUAL": record MANUAL, never execute anything.
- status == "MALFORMED" (from Step 3): record SKIPPED with a reason,
  never silently dropped.
- anything unexpected: record UNKNOWN with a reason, never silently
  dropped.

Writes harness_result_<component>.json to harness_results/. Does not
compare results against a committed checklist (drift detection) —
that is a later step. Does not wire into pre-push — that is Step 11.
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checklist import build_checklist, find_spec_files  # noqa: E402

DEFAULT_TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 4000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_markdown_code_span(text: str) -> str:
    """CHECKPOINT.md writes verify commands as a markdown code span
    (`` `command` ``); Step 3 extracted the literal line text, which
    still carries that single pair of enclosing backticks. Executed
    as-is, a leading/trailing backtick is shell command-substitution
    syntax, not part of the command — the shell would run the real
    command, capture its stdout, then try to execute THAT as a new
    command (confirmed empirically: `sh -c '`echo hi`'` ->
    "sh: hi: command not found"). Strip exactly one such wrapping
    pair before execution; leave anything else unchanged."""
    if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        return text[1:-1]
    return text


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + f"\n...[truncated, {len(text)} chars total]"


def run_automated(vc: dict, repo_root: Path, timeout: float) -> dict:
    raw_command = vc["verify_command"]
    command = _strip_markdown_code_span(raw_command)

    base = {
        "vc_id": vc["vc_id"],
        "label": vc.get("label"),
        "command": command,
        "timestamp": _now_iso(),
    }

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        return {
            **base,
            "result": "PASS" if proc.returncode == 0 else "FAIL",
            "exit_code": proc.returncode,
            "output_excerpt": _truncate(combined) if combined else "",
        }
    except subprocess.TimeoutExpired:
        return {
            **base,
            "result": "FAIL",
            "exit_code": None,
            "output_excerpt": None,
            "reason": f"timed out after {timeout}s",
        }
    except Exception as e:  # noqa: BLE001 - must never drop a VC silently
        return {
            **base,
            "result": "UNKNOWN",
            "exit_code": None,
            "output_excerpt": None,
            "reason": f"harness execution error: {e!r}",
        }


def process_vc(vc: dict, repo_root: Path, timeout: float) -> dict:
    """Never returns nothing for a VC — every path, including an
    unexpected exception, yields a recorded result."""
    try:
        if vc.get("status") == "MALFORMED":
            missing = ", ".join(vc.get("missing_fields") or []) or "unspecified"
            return {
                "vc_id": vc["vc_id"],
                "label": vc.get("label"),
                "command": None,
                "result": "SKIPPED",
                "exit_code": None,
                "output_excerpt": None,
                "reason": f"malformed VC — missing fields: {missing}",
                "timestamp": _now_iso(),
            }

        verify_type = vc.get("verify_type")

        if verify_type == "AUTOMATED":
            return run_automated(vc, repo_root, timeout)

        if verify_type == "MANUAL":
            return {
                "vc_id": vc["vc_id"],
                "label": vc.get("label"),
                "command": vc.get("verify_command"),
                "result": "MANUAL",
                "exit_code": None,
                "output_excerpt": None,
                "timestamp": _now_iso(),
            }

        return {
            "vc_id": vc.get("vc_id"),
            "label": vc.get("label"),
            "command": vc.get("verify_command"),
            "result": "UNKNOWN",
            "exit_code": None,
            "output_excerpt": None,
            "reason": f"unrecognized verify_type {verify_type!r} for a non-MALFORMED VC",
            "timestamp": _now_iso(),
        }
    except Exception as e:  # noqa: BLE001 - must never drop a VC silently
        return {
            "vc_id": vc.get("vc_id", "UNKNOWN-VC-ID"),
            "label": vc.get("label"),
            "command": None,
            "result": "UNKNOWN",
            "exit_code": None,
            "output_excerpt": None,
            "reason": f"harness error while processing VC: {e!r}",
            "timestamp": _now_iso(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root to scan (default: parent directory of scripts/)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-command timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    args = parser.parse_args()

    repo_root = (args.repo_root or Path(__file__).resolve().parent.parent).resolve()

    spec_files = find_spec_files(repo_root)
    if not spec_files:
        print("harness: no SPEC.md files found", file=sys.stderr)
        return 1

    owned_dirs = {p.parent.name for p in spec_files if p.parent != repo_root}

    # Resolve every component's checklist in memory before creating
    # harness_results/ itself — same self-inflicted-candidate-pollution
    # hazard Step 3 hit with checklists/, avoided the same way.
    built = [
        (spec_path, *build_checklist(spec_path, repo_root, owned_dirs))
        for spec_path in spec_files
    ]

    harness_dir = repo_root / "harness_results"
    harness_dir.mkdir(exist_ok=True)

    exit_code = 0

    for spec_path, checklist, ambiguous in built:
        component = checklist["component"]
        pattern = checklist["source_pattern"]

        if pattern == "UNKNOWN":
            print(
                f"harness: WARNING - {spec_path} has UNKNOWN VC-source "
                f"pattern; no checklist items to run, skipping.",
                file=sys.stderr,
            )
            exit_code = 1
            continue

        if ambiguous:
            print(
                f"harness: WARNING - could not unambiguously map "
                f"{spec_path} to a single component directory; best "
                f"guess is '{component}'.",
                file=sys.stderr,
            )

        results = []
        for vc in checklist["items"]:
            record = process_vc(vc, repo_root, args.timeout)
            results.append(record)
            if record["result"] in ("FAIL", "UNKNOWN"):
                exit_code = 1
                print(
                    f"harness: {record['result']} — {record['vc_id']} "
                    f"({record.get('reason', 'see output_excerpt')})",
                    file=sys.stderr,
                )

        summary = Counter(r["result"] for r in results)

        harness_output = {
            "component": component,
            "source_pattern": pattern,
            "checklist_source_file": checklist["source_file"],
            "generated_at": _now_iso(),
            "results": results,
        }

        out_path = harness_dir / f"harness_result_{component}.json"
        out_path.write_text(
            json.dumps(harness_output, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print(
            f"harness: {component} ({pattern}) -> {out_path} — "
            f"{len(results)} VCs: {summary.get('PASS', 0)} pass, "
            f"{summary.get('FAIL', 0)} fail, {summary.get('MANUAL', 0)} manual, "
            f"{summary.get('SKIPPED', 0)} skipped, {summary.get('UNKNOWN', 0)} unknown"
        )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
