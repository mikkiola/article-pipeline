#!/usr/bin/env python3
"""Lightweight ADR lifecycle check (docs/BACKLOG.md's "ADR lifecycle
state machine + structural validation" P2 item, lightweight piece):
confirms every docs/adr/*.md file's number is unique, and that its
header line's number matches its filename's number.

Does not implement the full lifecycle state machine (Proposed ->
Accepted -> Deprecated/Superseded) or the Supersedes/Superseded-by
field pair -- that piece is explicitly gated behind its own ADR
(see docs/adr/ next free number, DocOps SPEC.md M5) and is not
implemented here.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FILENAME_RE = re.compile(r"^(\d{4})-.+\.md$")
# Two header formats coexist in this repo: "# ADR-0032: Title" (0032+)
# and "# 0001 — Title" (0001-0031, pre-dating the "ADR-" prefix
# convention). Both are accepted -- this check validates the number,
# not a specific header text format CONSTITUTION.md doesn't mandate.
HEADER_RE = re.compile(r"^#\s*(?:ADR-)?(\d{4})\b", re.MULTILINE)


def check(adr_dir: Path) -> list[str]:
    """Returns a list of human-readable violation messages, empty if
    every file passes both checks."""
    violations: list[str] = []
    numbers: dict[str, list[str]] = {}

    for path in sorted(adr_dir.glob("*.md")):
        name_match = FILENAME_RE.match(path.name)
        if not name_match:
            violations.append(
                f"{path.name}: filename doesn't match the expected "
                "'NNNN-slug.md' pattern"
            )
            continue
        filename_number = name_match.group(1)

        text = path.read_text(encoding="utf-8")
        header_match = HEADER_RE.search(text)
        if not header_match:
            violations.append(
                f"{path.name}: no '# ADR-NNNN:' header line found"
            )
            continue
        header_number = header_match.group(1)

        if filename_number != header_number:
            violations.append(
                f"{path.name}: filename number ({filename_number}) does "
                f"not match header number ({header_number})"
            )

        numbers.setdefault(filename_number, []).append(path.name)

    for number, files in numbers.items():
        if len(files) > 1:
            violations.append(
                f"ADR number {number} used by multiple files: "
                f"{', '.join(files)}"
            )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adr-dir",
        default="docs/adr",
        help="Directory containing ADR files (default: docs/adr)",
    )
    args = parser.parse_args()

    adr_dir = Path(args.adr_dir)
    if not adr_dir.is_dir():
        print(f"[check_adr_numbering] FAIL: {adr_dir} is not a directory", file=sys.stderr)
        return 1

    violations = check(adr_dir)
    if violations:
        print(f"[check_adr_numbering] FAIL: {len(violations)} violation(s):", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print(f"[check_adr_numbering] OK: all ADRs in {adr_dir} numbered correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
