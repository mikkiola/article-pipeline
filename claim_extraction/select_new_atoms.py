"""
Driver for selecting N atoms not yet used in any prior pilot run.

select_pilot_atoms.py only dedupes within a single call (local `seen_paths`
set) - it doesn't know about atoms already spent in earlier pilot_run_*.json
files. This wrapper adds that cross-run exclusion on top, without touching
select_pilot_atoms.py or atom_selector.py (same "wrap outside, don't patch
the signature" pattern select_pilot_atoms.py itself already uses for
select_atom()).

Exclusion set is derived automatically by scanning every
output/pilot_run_*.json already on disk for its atom_path values - so this
keeps working correctly for run #5, #6, ... without hardcoding which atoms
were used before.

Usage: python3 select_new_atoms.py [N]  (default N=5)
Prints to stdout: {"atoms": [...], "skip_events": [...]}
(same shape as select_pilot_atoms.py, plus a "used_in_prior_run" skip type)
"""

import io
import os
import sys
import glob
import json
import contextlib
from datetime import datetime

import atom_selector
import graph_reader

MAX_ATTEMPTS_MULTIPLIER = 30

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def _already_used_atom_paths() -> set:
    """Absolute atom_paths seen in any existing output/pilot_run_*.json."""
    used = set()
    for run_file in glob.glob(os.path.join(OUTPUT_DIR, "pilot_run_*.json")):
        with open(run_file, "r", encoding="utf-8") as f:
            records = json.load(f)
        for record in records:
            rel_path = record["atom_path"]
            used.add(os.path.join(graph_reader.BRAIN_REPO_DIR, rel_path))
    return used


def select_new_atoms(n: int) -> tuple:
    excluded = _already_used_atom_paths()
    seen_paths = set()
    atoms = []
    skip_events = []

    captured = io.StringIO()
    max_attempts = n * MAX_ATTEMPTS_MULTIPLIER
    attempts = 0

    with contextlib.redirect_stdout(captured):
        while len(atoms) < n and attempts < max_attempts:
            attempts += 1
            result = atom_selector.select_atom()
            path = result["atom_path"]
            if path in excluded:
                print(f"[select_new_atoms] Skipping: atom already used in a prior run: {path}")
                continue
            if path in seen_paths:
                print(f"[select_new_atoms] Skipping duplicate (within this run): {path}")
                continue
            seen_paths.add(path)
            atoms.append({
                "cluster": result["cluster"],
                "atom_path": os.path.relpath(path, graph_reader.BRAIN_REPO_DIR),
                "atom_text": result["atom_text"],
            })

    console_log = captured.getvalue()
    for line in console_log.splitlines():
        if "already used in a prior run" in line:
            skip_events.append({"type": "used_in_prior_run", "detail": line})
        elif "Skipping duplicate" in line:
            skip_events.append({"type": "duplicate", "detail": line})
        elif "Пропуск файла" in line:
            skip_events.append({"type": "read_error", "detail": line})
        elif "Пропуск кластера" in line:
            skip_events.append({"type": "empty_cluster", "detail": line})

    if len(atoms) < n:
        raise RuntimeError(
            f"select_new_atoms: only gathered {len(atoms)} of {n} new atoms "
            f"in {attempts} attempts ({len(excluded)} already-used atoms excluded)."
        )

    return atoms, skip_events, console_log


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    atoms, skip_events, console_log = select_new_atoms(n)
    sys.stderr.write(console_log)
    print(json.dumps({
        "run_timestamp": datetime.now().isoformat(),
        "atoms": atoms,
        "skip_events": skip_events,
    }, ensure_ascii=False, indent=2))
