#!/usr/bin/env python3
"""Deliver-job gate: the stage 2 artifact -> the registry-data output tree.

The Deliver job holds the registry-data write credential, so what it commits
must not be decided by the job that handled model output. The artifact is
treated as untrusted input: only files of the two shapes stage 2 writes are
copied (`attempt_<N>.md` and exactly one `run_<run_id>.json`), nothing is
followed through a symlink or taken from a subdirectory, the run record's
outcome fields must agree with each other and its `attempt_files` must match
the attempt files present (names and sha256), and no file may match a secret
pattern. Any violation exits non-zero before a single file is staged, so the
commit step never sees a partial or foreign tree. Files are created
exclusively inside the given destination directory; that the destination is
the run's own `output/habr_draft/<run id>` directory is the workflow's
responsibility, not enforced here.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from habr_draft import run_record, secret_scan  # noqa: E402

ATTEMPT_RE = re.compile(r"^attempt_[1-9][0-9]*\.md$")
RUN_RECORD_RE = re.compile(r"^run_habr-draft-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{6}\.json$")


# observable outcomes of a run whose terminal_outcome is null
NULL_TERMINAL_OBSERVABLES = frozenset({"NO_ELIGIBLE_TOPIC", "CALIBRATION_RECORDED"})


class ArtifactRejected(Exception):
    """The artifact does not have the shape stage 2 produces."""


def validate_artifact(source: Path) -> list[Path]:
    """Returns the files to stage, or raises ArtifactRejected."""
    if not source.is_dir() or source.is_symlink():
        raise ArtifactRejected("artifact directory is missing")
    files: list[Path] = []
    records: list[Path] = []
    for entry in sorted(source.iterdir()):
        if entry.is_symlink() or not entry.is_file():
            raise ArtifactRejected(f"unexpected entry (not a regular file): {entry.name!r}")
        if RUN_RECORD_RE.fullmatch(entry.name):
            records.append(entry)
        elif not ATTEMPT_RE.fullmatch(entry.name):
            raise ArtifactRejected(f"unexpected file name: {entry.name!r}")
        files.append(entry)
    if len(records) != 1:
        raise ArtifactRejected(f"expected exactly one run record, found {len(records)}")

    try:
        record = json.loads(records[0].read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ArtifactRejected("run record is not valid UTF-8 JSON") from None
    if not isinstance(record, dict) or not record.get("observable_outcome"):
        raise ArtifactRejected("run record has no observable_outcome")
    try:
        run_record.validate_outcome(record.get("terminal_outcome"), record.get("failure_kind"))
    except ValueError as error:
        raise ArtifactRejected(f"run record outcome is inconsistent: {error}") from None
    if f"run_{record.get('run_id')}.json" != records[0].name:
        raise ArtifactRejected("run record name does not match its run_id")
    terminal, observable = record.get("terminal_outcome"), record["observable_outcome"]
    if terminal is not None and observable != terminal:
        raise ArtifactRejected("observable_outcome disagrees with terminal_outcome")
    if terminal is None and observable not in NULL_TERMINAL_OBSERVABLES:
        raise ArtifactRejected(f"unknown observable_outcome for a null terminal outcome: {observable!r}")
    declared = record.get("attempt_files")
    if not isinstance(declared, list):
        raise ArtifactRejected("run record has no attempt_files list")
    present = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
               for f in files if ATTEMPT_RE.fullmatch(f.name)}
    listed = {a.get("name"): a.get("sha256") for a in declared if isinstance(a, dict)}
    if listed != present or len(listed) != len(declared):
        raise ArtifactRejected("attempt files do not match the run record's attempt_files")

    patterns = secret_scan.load_patterns()  # a scan that cannot run is a failure
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ArtifactRejected(f"{path.name!r} is not UTF-8 text") from None
        if secret_scan.scan(text, patterns):
            raise ArtifactRejected(f"{path.name!r} matches a secret pattern")
    return files


def stage(source: Path, destination: Path) -> list[str]:
    files = validate_artifact(source)
    for path in files:  # all-or-nothing: a collision is found before any write
        if (destination / path.name).exists():
            raise FileExistsError(errno.EEXIST, "already exists", str(destination / path.name))
    destination.mkdir(parents=True, exist_ok=True)
    staged = []
    for path in files:
        run_record.write_new(destination / path.name, path.read_text(encoding="utf-8"))
        staged.append(path.name)
    return staged


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and stage the Habr draft artifact.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--destination", required=True,
                        help="registry-data output/habr_draft/<run id> directory")
    args = parser.parse_args()
    try:
        staged = stage(Path(args.artifact_dir), Path(args.destination))
    except ArtifactRejected as error:
        print(f"artifact rejected: {error}", file=sys.stderr)
        return 1
    except FileExistsError as error:
        print(f"artifact rejected: destination already holds {error.filename!r}", file=sys.stderr)
        return 1
    print(f"staged {len(staged)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
