#!/usr/bin/env python3
"""Component + VC-source-pattern discovery, plus structural validation.

Steps 1-2 of the SPEC -> checklist -> harness -> drift -> doc-sync
automation track.

Step 1: scans the repo for SPEC.md files and determines, for each,
which mechanism currently tracks that component's milestone/
verification state ("VC-source pattern"): a paired CHECKPOINT.md, or
milestone checkboxes inline in SPEC.md itself.

Step 2: for each discovered source_file, confirms it's structurally
parseable into individual verification-criteria-like units (a
CHECKPOINT.md "## <label>" block with verify:/done-when:/status:
lines, or an inline Milestones checkbox line with description text) —
and reports which units, if any, are malformed. Does not extract
actual VC-IDs or build a checklist — that's a later step.
"""
import argparse
import json
import re
import sys
from pathlib import Path

MILESTONES_HEADING_RE = re.compile(r"^##\s+Milestones\s*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^##\s+\S", re.MULTILINE)
CHECKBOX_LINE_RE = re.compile(r"^\s*(?:-|\d+\.)\s*\[[ xX]\]", re.MULTILINE)
CHECKBOX_FULL_LINE_RE = re.compile(r"^\s*(?:-|\d+\.)\s*\[[ xX]\](.*)$", re.MULTILINE)

CHECKPOINT_BLOCK_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
CHECKPOINT_REQUIRED_FIELD_RES = {
    "verify": re.compile(r"^\s*-\s*verify:", re.MULTILINE),
    "done-when": re.compile(r"^\s*-\s*done-when:", re.MULTILINE),
    "status": re.compile(r"^\s*-\s*status:", re.MULTILINE),
}

# Directories that hold project infrastructure, not a pipeline
# component, and are therefore never SPEC.md/component candidates.
NON_COMPONENT_DIRS = {"docs", "scripts"}


def find_spec_files(repo_root: Path) -> list[Path]:
    """SPEC.md at repo root, plus SPEC.md directly inside any
    immediate subdirectory. Does not recurse further, does not
    hardcode any specific file path."""
    found = []
    root_spec = repo_root / "SPEC.md"
    if root_spec.is_file():
        found.append(root_spec)
    for child in sorted(repo_root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name in NON_COMPONENT_DIRS:
            continue
        candidate = child / "SPEC.md"
        if candidate.is_file():
            found.append(candidate)
    return found


def component_candidate_dirs(repo_root: Path, owned_dirs: set) -> list:
    """Immediate subdirectories that could be the component a
    root-level SPEC.md documents: excludes infra dirs and any
    directory that already owns its own SPEC.md (that directory's
    component identity is already resolved directly, not inferred)."""
    dirs = []
    for child in sorted(repo_root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name in NON_COMPONENT_DIRS:
            continue
        if child.name in owned_dirs:
            continue
        dirs.append(child.name)
    return dirs


def resolve_component_name(spec_path: Path, repo_root: Path, owned_dirs: set):
    """Returns (component_name, ambiguous).

    A SPEC.md living directly inside a component directory: that
    directory's name IS the component name, unambiguous.

    A SPEC.md at repo root: the component it documents isn't given by
    its own location, so it's inferred from its text. Strong signal:
    an explicit "<repo-dir-name>/<component>/" path (the pattern a
    SPEC's own "code location" section uses to state where a
    component's code actually lives). Fallback: bare "<component>/"
    occurrence count. If neither resolves to a single candidate,
    ambiguous=True and a best guess is still returned.
    """
    parent = spec_path.parent
    if parent != repo_root:
        return parent.name, False

    text = spec_path.read_text(encoding="utf-8")
    candidates = component_candidate_dirs(repo_root, owned_dirs)
    if not candidates:
        return repo_root.name, True

    strong_counts = {
        d: len(re.findall(re.escape(f"{repo_root.name}/{d}/"), text))
        for d in candidates
    }
    strong_hits = {d: c for d, c in strong_counts.items() if c > 0}
    if len(strong_hits) == 1:
        return next(iter(strong_hits)), False

    bare_counts = {
        d: len(re.findall(re.escape(f"{d}/"), text)) for d in candidates
    }
    max_count = max(bare_counts.values(), default=0)
    top = [d for d, c in bare_counts.items() if c == max_count and c > 0]
    if len(top) == 1:
        return top[0], False

    best_guess = sorted(top)[0] if top else sorted(candidates)[0]
    return best_guess, True


def isolate_milestones_section(text: str):
    """Returns (section_text, section_start_offset), or (None, None)
    if there's no "## Milestones" heading. section_start_offset is
    the absolute offset of the section's start within `text`, used to
    recover real line numbers for anything found inside it."""
    match = MILESTONES_HEADING_RE.search(text)
    if not match:
        return None, None
    start = match.end()
    rest = text[start:]
    next_heading = NEXT_HEADING_RE.search(rest)
    end = start + (next_heading.start() if next_heading else len(rest))
    return text[start:end], start


def has_milestones_checkboxes(spec_path: Path) -> bool:
    text = spec_path.read_text(encoding="utf-8")
    section, _ = isolate_milestones_section(text)
    if section is None:
        return False
    return bool(CHECKBOX_LINE_RE.search(section))


def classify(spec_path: Path):
    """Returns (pattern, source_file).

    pattern is one of "checkpoint" / "inline_spec" / "UNKNOWN".
    "UNKNOWN" means neither a paired CHECKPOINT.md nor an inline
    Milestones checklist was found — the component has zero tracked
    verification criteria, and this must never pass through silently.
    """
    checkpoint_path = spec_path.parent / "CHECKPOINT.md"
    if checkpoint_path.is_file():
        return "checkpoint", str(checkpoint_path)
    if has_milestones_checkboxes(spec_path):
        return "inline_spec", str(spec_path)
    return "UNKNOWN", None


def validate_checkpoint_structure(checkpoint_path: str) -> dict:
    """A well-formed CHECKPOINT.md is a sequence of "## <label>"
    blocks, each containing its own verify:/done-when:/status: lines.
    Reports which blocks, if any, are missing which of the three."""
    text = Path(checkpoint_path).read_text(encoding="utf-8")
    headings = list(CHECKPOINT_BLOCK_HEADING_RE.finditer(text))

    if not headings:
        return {
            "status": "MALFORMED",
            "total_units": 0,
            "well_formed": 0,
            "malformed_details": [
                {"heading": None, "missing_fields": ["no '## <label>' blocks found"]}
            ],
        }

    total_units = len(headings)
    well_formed = 0
    malformed_details = []

    for i, match in enumerate(headings):
        heading = match.group(1).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        content = text[start:end]

        missing = [
            name
            for name, pattern in CHECKPOINT_REQUIRED_FIELD_RES.items()
            if not pattern.search(content)
        ]
        if missing:
            malformed_details.append({"heading": heading, "missing_fields": missing})
        else:
            well_formed += 1

    status = "MALFORMED" if malformed_details else "OK"
    return {
        "status": status,
        "total_units": total_units,
        "well_formed": well_formed,
        "malformed_details": malformed_details,
    }


def validate_inline_spec_structure(spec_path: str) -> dict:
    """Within the Milestones section (isolated via the same
    MILESTONES_HEADING_RE/NEXT_HEADING_RE logic Step 1 uses), each
    checkbox line must carry non-empty description text after the
    checkbox marker on that same line."""
    text = Path(spec_path).read_text(encoding="utf-8")
    section, section_start = isolate_milestones_section(text)

    if section is None:
        return {
            "status": "MALFORMED",
            "total_units": 0,
            "well_formed": 0,
            "malformed_details": [
                {"line": None, "text": "no '## Milestones' section found"}
            ],
        }

    matches = list(CHECKBOX_FULL_LINE_RE.finditer(section))
    if not matches:
        return {
            "status": "MALFORMED",
            "total_units": 0,
            "well_formed": 0,
            "malformed_details": [
                {"line": None, "text": "no checkbox lines found in Milestones section"}
            ],
        }

    total_units = len(matches)
    well_formed = 0
    malformed_details = []

    for match in matches:
        description = match.group(1).strip()
        if description:
            well_formed += 1
        else:
            abs_pos = section_start + match.start()
            line_no = text[:abs_pos].count("\n") + 1
            malformed_details.append({"line": line_no, "text": match.group(0).strip()})

    status = "MALFORMED" if malformed_details else "OK"
    return {
        "status": status,
        "total_units": total_units,
        "well_formed": well_formed,
        "malformed_details": malformed_details,
    }


def validate_structure(pattern: str, source_file) -> dict:
    if pattern == "checkpoint":
        return validate_checkpoint_structure(source_file)
    if pattern == "inline_spec":
        return validate_inline_spec_structure(source_file)
    return {"status": "UNKNOWN", "total_units": 0, "well_formed": 0, "malformed_details": []}


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
        print("discover: no SPEC.md files found", file=sys.stderr)
        return 1

    # Resolve directories that own their own SPEC.md directly first,
    # so a root-level SPEC.md's inference excludes them as candidates.
    owned_dirs = {p.parent.name for p in spec_files if p.parent != repo_root}

    results = []

    for spec_path in spec_files:
        component, ambiguous = resolve_component_name(spec_path, repo_root, owned_dirs)
        pattern, source_file = classify(spec_path)

        if pattern == "UNKNOWN":
            print(
                f"discover: WARNING - {spec_path} has no CHECKPOINT.md and no "
                f"'## Milestones' section with checkbox lines. VC-source "
                f"pattern is UNKNOWN for this component; it carries zero "
                f"tracked verification criteria until this is resolved.",
                file=sys.stderr,
            )
        if ambiguous:
            print(
                f"discover: WARNING - could not unambiguously map {spec_path} "
                f"to a single component directory; best guess is "
                f"'{component}'.",
                file=sys.stderr,
            )

        structure = validate_structure(pattern, source_file)
        for detail in structure["malformed_details"]:
            if "heading" in detail:
                print(
                    f"discover: MALFORMED block in {source_file} — heading "
                    f"'{detail['heading']}' is missing: "
                    f"{', '.join(detail['missing_fields'])}",
                    file=sys.stderr,
                )
            else:
                where = f"{source_file}:{detail['line']}" if detail["line"] else source_file
                print(
                    f"discover: MALFORMED unit at {where} — {detail['text']!r}",
                    file=sys.stderr,
                )

        results.append(
            {
                "component": component,
                "spec_path": str(spec_path),
                "pattern": pattern,
                "source_file": source_file,
                "structure": structure,
            }
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))

    any_not_ok = any(r["structure"]["status"] != "OK" for r in results)
    return 1 if any_not_ok else 0


if __name__ == "__main__":
    sys.exit(main())
