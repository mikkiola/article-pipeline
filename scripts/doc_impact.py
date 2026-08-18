#!/usr/bin/env python3
"""Documentation impact detection (brief §16).

Step 7 of the SPEC -> checklist -> harness -> drift -> doc-sync
automation track. Classifies every file in a git diff range as
NO_IMPACT, DERIVED_UPDATE_REQUIRED, ARCHITECTURAL_REVIEW_REQUIRED, or
UNKNOWN, per fixed, literal rules inferable from Steps 1-6's own
findings — nothing invented beyond what's specified.

This is classification only: it does not update any documentation
(Step 8), does not change the existing pre-push hook's warning
(Step 11), and does not touch scripts/verify.py, checklist.py,
harness.py, or drift.py.

Component discovery reuses scripts/checklist.py's build_checklist()
(imported, not duplicated). The "does a changed code file's name
appear in its component's own SPEC text" signal reuses Step 6 part
(C)'s exact file-naming extraction via
scripts/drift.py's check_implementation_signals() (imported, not
reimplemented).
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checklist import build_checklist, find_spec_files  # noqa: E402
from drift import check_implementation_signals  # noqa: E402

import subprocess  # noqa: E402

GENERATED_DIRS = ("checklists", "harness_results", "drift_reports")
ADR_DIR = "docs/adr/"
ARCHITECTURE_DOC = "docs/ARCHITECTURE.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_changed_files(repo_root: Path, since: str | None):
    if since:
        cmd = ["git", "diff", "--name-only", since, "HEAD"]
        description = f"git diff --name-only {since} HEAD"
    else:
        cmd = ["git", "diff", "--name-only", "HEAD"]
        description = "git diff --name-only HEAD (working tree + staged changes vs HEAD)"

    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"'{' '.join(cmd)}' failed (exit {proc.returncode}): {proc.stderr.strip()}"
        )
    files = sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())
    return files, description


def discover_components(repo_root: Path) -> dict:
    """component -> {dir, spec_path, source_file, pattern}, reusing
    Steps 1-3's own discovery/classification (find_spec_files,
    build_checklist) rather than any new heuristic."""
    spec_files = find_spec_files(repo_root)
    if not spec_files:
        return {}

    owned_dirs = {p.parent.name for p in spec_files if p.parent != repo_root}
    components = {}
    for spec_path in spec_files:
        checklist, _ambiguous = build_checklist(spec_path, repo_root, owned_dirs)
        component = checklist["component"]
        pattern = checklist["source_pattern"]
        if pattern == "UNKNOWN":
            continue
        components[component] = {
            "dir": repo_root / component,
            "spec_path": spec_path,
            "source_file": checklist["source_file"],
            "pattern": pattern,
        }
    return components


def _spec_related_paths(component: str, components: dict, repo_root: Path) -> set:
    meta = components[component]
    spec_rel = str(meta["spec_path"].resolve().relative_to(repo_root))
    source_rel = str(Path(meta["source_file"]).resolve().relative_to(repo_root))
    return {spec_rel, source_rel}


def spec_file_owner(rel_path: str, components: dict, repo_root: Path):
    for component in components:
        if rel_path in _spec_related_paths(component, components, repo_root):
            return component
    return None


def code_file_owner(rel_path: str, components: dict):
    """The component owning this file's code directory, excluding any
    'output/' subdirectory (brief's explicit carve-out) — returns None
    for a file under <component>/output/, same as for a file under no
    known component at all."""
    parts = Path(rel_path).parts
    if not parts or parts[0] not in components:
        return None
    if "output" in parts[1:]:
        return None
    return parts[0]


def component_output_owner(rel_path: str, components: dict):
    parts = Path(rel_path).parts
    if not parts or parts[0] not in components:
        return None
    if "output" in parts[1:]:
        return parts[0]
    return None


def spec_named_files(repo_root: Path, component: str, components: dict) -> set:
    """Reuses Step 6 part (C)'s exact file-naming extraction
    (scripts/drift.py's check_implementation_signals) rather than
    reimplementing the `<component>/<file>.py` regex. Only the set of
    named-file paths is used here; existence is irrelevant to this
    step's own question (whether the changed file IS one of them)."""
    meta = components[component]
    findings = check_implementation_signals(
        repo_root, component, meta["spec_path"], meta["source_file"]
    )
    return {f["file"] for f in findings if "file" in f}


def classify_file(
    rel_path: str,
    components: dict,
    changed_set: set,
    architecture_changed: bool,
    repo_root: Path,
) -> tuple:
    if any(rel_path == d or rel_path.startswith(f"{d}/") for d in GENERATED_DIRS):
        return "NO_IMPACT", (
            f"{rel_path} is inside a generated-artifact directory "
            f"({'/'.join(GENERATED_DIRS)}) — a derived output of this "
            f"automation track's own scripts, not a source of doc-relevant change."
        )

    if rel_path.startswith(ADR_DIR) and rel_path.endswith(".md"):
        return "ARCHITECTURAL_REVIEW_REQUIRED", f"{rel_path} is an ADR file — ADRs are never routine."

    spec_owner = spec_file_owner(rel_path, components, repo_root)
    if spec_owner is not None:
        if not architecture_changed:
            return "DERIVED_UPDATE_REQUIRED", (
                f"{rel_path} is {spec_owner}'s SPEC/CHECKPOINT source, changed "
                f"with no corresponding {ARCHITECTURE_DOC} change in this range."
            )
        return "UNKNOWN", (
            f"{rel_path} is {spec_owner}'s SPEC/CHECKPOINT source, changed "
            f"together with {ARCHITECTURE_DOC} in this range — none of the "
            f"specified rules define a classification for this already-paired "
            f"case; not guessing one."
        )

    code_owner = code_file_owner(rel_path, components)
    if code_owner is not None:
        spec_paths = _spec_related_paths(code_owner, components, repo_root)
        spec_changed = bool(spec_paths & changed_set)
        if not spec_changed:
            named_files = spec_named_files(repo_root, code_owner, components)
            if rel_path in named_files:
                return "ARCHITECTURAL_REVIEW_REQUIRED", (
                    f"{rel_path} is a {code_owner} code file literally named in "
                    f"{code_owner}'s own SPEC text (Step 6 part C's file-naming "
                    f"logic), changed with no corresponding SPEC.md/CHECKPOINT.md "
                    f"update in this range."
                )
            return "DERIVED_UPDATE_REQUIRED", (
                f"{rel_path} is a {code_owner} code file not itself named in the "
                f"SPEC text, changed with no corresponding SPEC.md/CHECKPOINT.md "
                f"update in this range."
            )
        return "UNKNOWN", (
            f"{rel_path} is a {code_owner} code file, changed together with its "
            f"SPEC.md/CHECKPOINT.md in this range — none of the specified rules "
            f"define a classification for this already-paired case; not "
            f"guessing one."
        )

    output_owner = component_output_owner(rel_path, components)
    if output_owner is not None:
        return "UNKNOWN", (
            f"{rel_path} is inside {output_owner}/output/, a component-owned "
            f"generated-output subdirectory explicitly excluded from the "
            f"code-file rule's scope; not covered by any other specified rule."
        )

    return "UNKNOWN", (
        f"{rel_path} does not match any specified rule: not a generated-artifact "
        f"directory, not {ADR_DIR}, not a known component's SPEC/CHECKPOINT "
        f"source, and not inside a known component's code directory."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root to scan (default: parent directory of scripts/)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help=(
            "Git ref to diff against HEAD (e.g. a commit SHA). Default: "
            "working tree + staged changes vs HEAD."
        ),
    )
    args = parser.parse_args()

    repo_root = (args.repo_root or Path(__file__).resolve().parent.parent).resolve()

    try:
        changed_files, diff_description = get_changed_files(repo_root, args.since)
    except RuntimeError as e:
        print(f"doc_impact: {e}", file=sys.stderr)
        return 1

    if not changed_files:
        print(f"doc_impact: no changed files in range ({diff_description})", file=sys.stderr)

    components = discover_components(repo_root)
    changed_set = set(changed_files)
    architecture_changed = ARCHITECTURE_DOC in changed_set

    findings = [
        {
            "file": rel_path,
            "classification": classification,
            "reason": reason,
        }
        for rel_path in changed_files
        for classification, reason in [
            classify_file(rel_path, components, changed_set, architecture_changed, repo_root)
        ]
    ]

    summary = Counter(f["classification"] for f in findings)

    report = {
        "generated_at": _now_iso(),
        "diff_range": {"since": args.since, "command": diff_description},
        "changed_files_count": len(findings),
        "findings": findings,
        "summary": {
            "NO_IMPACT": summary.get("NO_IMPACT", 0),
            "DERIVED_UPDATE_REQUIRED": summary.get("DERIVED_UPDATE_REQUIRED", 0),
            "ARCHITECTURAL_REVIEW_REQUIRED": summary.get("ARCHITECTURAL_REVIEW_REQUIRED", 0),
            "UNKNOWN": summary.get("UNKNOWN", 0),
        },
    }

    out_dir = repo_root / "doc_reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "doc_impact_report.json"
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"doc_impact: {len(findings)} changed files ({diff_description}) -> {out_path}")
    s = report["summary"]
    print(
        f"doc_impact: {s['NO_IMPACT']} no_impact, "
        f"{s['DERIVED_UPDATE_REQUIRED']} derived_update_required, "
        f"{s['ARCHITECTURAL_REVIEW_REQUIRED']} architectural_review_required, "
        f"{s['UNKNOWN']} unknown"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
