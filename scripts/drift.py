#!/usr/bin/env python3
"""Drift detection: SPEC <-> checklist, checklist <-> harness,
implementation <-> SPEC (mechanical signals only).

Step 6 of the SPEC -> checklist -> harness -> drift -> doc-sync
automation track. Reuses Step 3's checklist generation from
scripts/checklist.py (imported, not duplicated) to regenerate a fresh
checklist from the current SPEC/CHECKPOINT source, then compares it
against the currently committed checklists/checklist_<component>.json
and harness_results/harness_result_<component>.json on disk.

Only detects and reports — never auto-fixes, never modifies
checklist.py/harness.py/verify.py, never touches SPEC.md/CHECKPOINT.md.
Not wired into pre-push (that's Step 11).

Part (C) does not attempt semantic proof that an implementation
matches its SPEC — only mechanical `<component>/<file>.py` mentions
found in the component's own SPEC text (plus its paired CHECKPOINT.md
for the checkpoint pattern) are checked for existence. Everything else
about implementation<->SPEC conformance is reported as a standing
POTENTIAL DRIFT note, not attempted.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checklist import build_checklist, find_spec_files  # noqa: E402

COMPARE_FIELDS = ("label", "verify_command", "verify_type", "done_when", "status")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path):
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def compare_spec_to_checklist(fresh_checklist: dict, committed_checklist: dict | None) -> list:
    """Part (A), brief §13 — fully deterministic. Compares the freshly
    regenerated VC set against the committed checklist file's VC set,
    both by ID and by the 5 comparable per-item fields."""
    findings = []
    fresh_items = {item["vc_id"]: item for item in fresh_checklist["items"]}
    committed_items = {
        item["vc_id"]: item for item in (committed_checklist or {}).get("items", [])
    }

    fresh_ids = set(fresh_items)
    committed_ids = set(committed_items)

    for vc_id in sorted(fresh_ids - committed_ids):
        findings.append(
            {
                "type": "DRIFT",
                "category": "missing_from_checklist",
                "vc_id": vc_id,
                "message": f"Missing: {vc_id}",
            }
        )

    for vc_id in sorted(committed_ids - fresh_ids):
        findings.append(
            {
                "type": "DRIFT",
                "category": "unmapped_checklist_item",
                "vc_id": vc_id,
                "message": f"Unmapped checklist item: {vc_id}",
            }
        )

    for vc_id in sorted(fresh_ids & committed_ids):
        fresh_item = fresh_items[vc_id]
        committed_item = committed_items[vc_id]
        changed = [
            {"field": field, "old": committed_item.get(field), "new": fresh_item.get(field)}
            for field in COMPARE_FIELDS
            if fresh_item.get(field) != committed_item.get(field)
        ]
        if changed:
            findings.append(
                {
                    "type": "DRIFT",
                    "category": "changed",
                    "vc_id": vc_id,
                    "message": f"Changed: {vc_id}",
                    "fields": changed,
                }
            )

    if not findings:
        findings.append(
            {
                "type": "CLEAN",
                "message": "Fresh SPEC/CHECKPOINT regeneration matches the committed checklist exactly.",
            }
        )

    return findings


def compare_checklist_to_harness(checklist: dict, harness_result: dict | None) -> list:
    """Part (B), brief §14. Checklist VC with no harness entry ->
    UNVERIFIED. Harness entry with no checklist VC -> DRIFT,
    "Unscoped validation" (brief §7)."""
    findings = []
    checklist_ids = {item["vc_id"] for item in checklist["items"]}
    harness_ids = {r["vc_id"] for r in (harness_result or {}).get("results", [])}

    for vc_id in sorted(checklist_ids - harness_ids):
        findings.append(
            {
                "type": "UNVERIFIED",
                "vc_id": vc_id,
                "message": f"Unverified: {vc_id} — no harness result entry found for this checklist VC.",
            }
        )

    for vc_id in sorted(harness_ids - checklist_ids):
        findings.append(
            {
                "type": "DRIFT",
                "category": "unscoped_validation",
                "vc_id": vc_id,
                "message": f"Unscoped validation: {vc_id}",
            }
        )

    if not findings:
        findings.append(
            {
                "type": "CLEAN",
                "message": "Checklist and harness result VC sets match exactly.",
            }
        )

    return findings


def check_implementation_signals(
    repo_root: Path, component: str, spec_path: Path, source_file: str
) -> list:
    """Part (C), brief §15 — safe mechanical signals only. Extracts
    literal `<component>/<file>.py` mentions from the component's own
    SPEC text (plus its paired CHECKPOINT.md when that's a distinct
    file, i.e. the checkpoint pattern) and checks each named file
    actually exists. Everything else about implementation<->SPEC
    conformance is out of mechanical reach."""
    findings = []

    texts = [Path(spec_path).read_text(encoding="utf-8")]
    if str(source_file) != str(spec_path):
        texts.append(Path(source_file).read_text(encoding="utf-8"))

    file_mention_re = re.compile(rf"\b{re.escape(component)}/([A-Za-z_][A-Za-z0-9_]*\.py)\b")
    named_files = set()
    for text in texts:
        named_files.update(file_mention_re.findall(text))

    component_dir = repo_root / component
    for filename in sorted(named_files):
        rel = f"{component}/{filename}"
        if (component_dir / filename).is_file():
            findings.append({"type": "CLEAN", "file": rel, "message": f"Present: {rel}"})
        else:
            findings.append(
                {
                    "type": "DRIFT",
                    "category": "missing_implementation_file",
                    "file": rel,
                    "message": f"Missing implementation file named in SPEC/CHECKPOINT: {rel}",
                }
            )

    if not named_files:
        findings.append(
            {
                "type": "POTENTIAL DRIFT",
                "message": (
                    f"No mechanically-checkable `{component}/<file>.py` mentions found "
                    f"in this component's SPEC text."
                ),
            }
        )

    findings.append(
        {
            "type": "POTENTIAL DRIFT",
            "message": (
                "Semantic conformance between implementation and SPEC (requirements "
                "coverage, behavior correctness beyond file existence) is not "
                "mechanically checkable — requires human review."
            ),
        }
    )

    return findings


def build_drift_report(
    repo_root: Path, spec_path: Path, fresh_checklist: dict
) -> dict:
    component = fresh_checklist["component"]

    checklist_path = repo_root / "checklists" / f"checklist_{component}.json"
    committed_checklist = _load_json(checklist_path)

    harness_path = repo_root / "harness_results" / f"harness_result_{component}.json"
    harness_result = _load_json(harness_path)

    section_a = compare_spec_to_checklist(fresh_checklist, committed_checklist)
    section_b = compare_checklist_to_harness(fresh_checklist, harness_result)
    section_c = check_implementation_signals(
        repo_root, component, spec_path, fresh_checklist["source_file"]
    )

    summary = Counter(f["type"] for f in section_a + section_b + section_c)

    return {
        "component": component,
        "generated_at": _now_iso(),
        "spec_vs_checklist": {
            "committed_checklist_path": str(checklist_path),
            "findings": section_a,
        },
        "checklist_vs_harness": {
            "harness_result_path": str(harness_path),
            "findings": section_b,
        },
        "implementation_vs_spec": {
            "findings": section_c,
        },
        "summary": {
            "DRIFT": summary.get("DRIFT", 0),
            "UNVERIFIED": summary.get("UNVERIFIED", 0),
            "CLEAN": summary.get("CLEAN", 0),
            "POTENTIAL DRIFT": summary.get("POTENTIAL DRIFT", 0),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root to scan (default: parent directory of scripts/)",
    )
    args = parser.parse_args()

    repo_root = (args.repo_root or Path(__file__).resolve().parent.parent).resolve()

    spec_files = find_spec_files(repo_root)
    if not spec_files:
        print("drift: no SPEC.md files found", file=sys.stderr)
        return 1

    owned_dirs = {p.parent.name for p in spec_files if p.parent != repo_root}

    built = [
        (spec_path, *build_checklist(spec_path, repo_root, owned_dirs))
        for spec_path in spec_files
    ]

    drift_dir = repo_root / "drift_reports"
    drift_dir.mkdir(exist_ok=True)

    exit_code = 0

    for spec_path, fresh_checklist, ambiguous in built:
        component = fresh_checklist["component"]
        pattern = fresh_checklist["source_pattern"]

        if pattern == "UNKNOWN":
            print(
                f"drift: WARNING - {spec_path} has UNKNOWN VC-source "
                f"pattern; skipping.",
                file=sys.stderr,
            )
            exit_code = 1
            continue

        if ambiguous:
            print(
                f"drift: WARNING - could not unambiguously map {spec_path} "
                f"to a single component directory; best guess is "
                f"'{component}'.",
                file=sys.stderr,
            )

        report = build_drift_report(repo_root, spec_path, fresh_checklist)

        out_path = drift_dir / f"drift_report_{component}.json"
        out_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        summary = report["summary"]
        if summary["DRIFT"] > 0:
            exit_code = 1

        print(
            f"drift: {component} -> {out_path} — "
            f"{summary['DRIFT']} drift, {summary['UNVERIFIED']} unverified, "
            f"{summary['CLEAN']} clean, {summary['POTENTIAL DRIFT']} potential drift"
        )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
