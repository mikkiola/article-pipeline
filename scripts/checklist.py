#!/usr/bin/env python3
"""SPEC -> checklist generation.

Step 3 of the SPEC -> checklist -> harness -> drift -> doc-sync
automation track. Reuses Step 1/2's discovery and classification
logic from scripts/verify.py (imported, not duplicated) to find each
component's SPEC.md and its VC-source pattern (checkpoint /
inline_spec), then extracts one verification-criterion (VC) item per
tracked unit and writes checklist_<component>.json to checklists/.

Does not compare generated output against a committed checklist
(drift detection) — that is a later step.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify import (  # noqa: E402
    CHECKBOX_FULL_LINE_RE,
    CHECKBOX_LINE_RE,
    CHECKPOINT_BLOCK_HEADING_RE,
    CHECKPOINT_REQUIRED_FIELD_RES,
    classify,
    find_spec_files,
    isolate_milestones_section,
    resolve_component_name,
)

VERIFY_LINE_RE = re.compile(r"^\s*-\s*verify:\s*(.*)$", re.MULTILINE)
DONE_WHEN_LINE_RE = re.compile(r"^\s*-\s*done-when:\s*(.*)$", re.MULTILINE)
STATUS_LINE_RE = re.compile(r"^\s*-\s*status:\s*(.*)$", re.MULTILINE)

MANUAL_MARKERS = ("ручная проверка", "не автоматизируется")


def _is_manual_verify_text(text: str) -> bool:
    if text.strip() == "—":
        return True
    return any(marker in text for marker in MANUAL_MARKERS)


def generate_checkpoint_items(checkpoint_path: str, component: str) -> list:
    """One VC per '## <label>' block in a CHECKPOINT.md. A block
    missing any of verify:/done-when:/status: is emitted with an
    explicit status="MALFORMED" marker instead of a silently
    incomplete normal item."""
    text = Path(checkpoint_path).read_text(encoding="utf-8")
    headings = list(CHECKPOINT_BLOCK_HEADING_RE.finditer(text))

    items = []
    for i, match in enumerate(headings):
        heading = match.group(1).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        content = text[start:end]
        vc_id = f"{component}-VC-{i + 1:03d}"

        missing = [
            name
            for name, pattern in CHECKPOINT_REQUIRED_FIELD_RES.items()
            if not pattern.search(content)
        ]
        if missing:
            items.append(
                {
                    "vc_id": vc_id,
                    "label": heading,
                    "verify_command": None,
                    "verify_type": None,
                    "done_when": None,
                    "status": "MALFORMED",
                    "malformed": True,
                    "missing_fields": missing,
                }
            )
            continue

        verify_text = VERIFY_LINE_RE.search(content).group(1).strip()
        done_when_text = DONE_WHEN_LINE_RE.search(content).group(1).strip()
        status_text = STATUS_LINE_RE.search(content).group(1).strip()

        items.append(
            {
                "vc_id": vc_id,
                "label": heading,
                "verify_command": verify_text,
                "verify_type": "MANUAL" if _is_manual_verify_text(verify_text) else "AUTOMATED",
                "done_when": done_when_text,
                "status": "DONE" if status_text == "done" else "NOT_STARTED",
            }
        )
    return items


def generate_inline_spec_items(spec_path: str, component: str) -> list:
    """One VC per Milestones checkbox item in a SPEC.md. A milestone's
    description commonly wraps across several physical lines (no
    blank line, no next marker until the item ends) — CHECKBOX_FULL_LINE_RE
    only matches the first such line, so it's used here just to locate
    each checkbox marker's start position; the full item text is then
    sliced from that position to the next marker (or section end) and
    the marker itself stripped with CHECKBOX_LINE_RE, so a wrapped
    description isn't truncated mid-sentence. Neither regex is
    modified — both are scripts/verify.py's, reused as-is, so Step 2's
    single-line-based validation there is unaffected.

    verify_command is always null and done_when is always "UNKNOWN" —
    the SPEC's Test Plan describes verification at the SPEC level, not
    per-Milestone, and inferring that mapping would be guessing, not
    extraction."""
    text = Path(spec_path).read_text(encoding="utf-8")
    section, _ = isolate_milestones_section(text)
    if section is None:
        return []

    matches = list(CHECKBOX_FULL_LINE_RE.finditer(section))
    items = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        block = section[start:end]

        is_done = "[x]" in match.group(0).lower()
        description = CHECKBOX_LINE_RE.sub("", block, count=1)
        description = " ".join(description.split())

        vc_id = f"{component}-VC-{i + 1:03d}"
        items.append(
            {
                "vc_id": vc_id,
                "label": description,
                "verify_command": None,
                "verify_type": "MANUAL",
                "done_when": "UNKNOWN",
                "status": "DONE" if is_done else "NOT_STARTED",
            }
        )
    return items


def build_checklist(spec_path: Path, repo_root: Path, owned_dirs: set):
    component, ambiguous = resolve_component_name(spec_path, repo_root, owned_dirs)
    pattern, source_file = classify(spec_path)

    if pattern == "checkpoint":
        items = generate_checkpoint_items(source_file, component)
    elif pattern == "inline_spec":
        items = generate_inline_spec_items(source_file, component)
    else:
        items = []

    checklist = {
        "component": component,
        "source_pattern": pattern,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    return checklist, ambiguous


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
        print("checklist: no SPEC.md files found", file=sys.stderr)
        return 1

    owned_dirs = {p.parent.name for p in spec_files if p.parent != repo_root}

    # Resolve every component and build its checklist content in memory
    # before creating checklists/ itself: resolve_component_name's
    # ambiguous-fallback path scans repo_root's immediate subdirectories
    # as candidates, and this script's own output directory must never
    # be one of them (matters on a repo root with no other component
    # subdirs to disambiguate against, e.g. a scratch/mutation-test copy).
    built = [
        (spec_path, *build_checklist(spec_path, repo_root, owned_dirs))
        for spec_path in spec_files
    ]

    checklists_dir = repo_root / "checklists"
    checklists_dir.mkdir(exist_ok=True)

    exit_code = 0

    for spec_path, checklist, ambiguous in built:
        component = checklist["component"]
        pattern = checklist["source_pattern"]

        if pattern == "UNKNOWN":
            print(
                f"checklist: WARNING - {spec_path} has UNKNOWN VC-source "
                f"pattern; no checklist generated.",
                file=sys.stderr,
            )
            exit_code = 1
            continue

        if ambiguous:
            print(
                f"checklist: WARNING - could not unambiguously map "
                f"{spec_path} to a single component directory; best guess "
                f"is '{component}'.",
                file=sys.stderr,
            )

        malformed = [item for item in checklist["items"] if item.get("malformed")]
        for item in malformed:
            exit_code = 1
            print(
                f"checklist: MALFORMED block '{item['label']}' in "
                f"{checklist['source_file']} — missing: "
                f"{', '.join(item['missing_fields'])}. Emitted {item['vc_id']} "
                f"with status=MALFORMED, not a normal VC.",
                file=sys.stderr,
            )

        out_path = checklists_dir / f"checklist_{component}.json"
        out_path.write_text(
            json.dumps(checklist, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        done_count = sum(1 for item in checklist["items"] if item["status"] == "DONE")
        print(
            f"checklist: {component} ({pattern}) -> {out_path} — "
            f"{len(checklist['items'])} VCs, {done_count} done, "
            f"{len(malformed)} malformed"
        )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
