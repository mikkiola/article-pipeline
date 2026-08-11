"""
Драйвер отбора N уникальных атомов для пилота Claim Extraction.

select_atom() (см. atom_selector.py) не гарантирует уникальность между
вызовами — ротация по кластеру снаружи, random.choice внутри кластера без
дедупликации. Решение по SPEC.md: не патчить сигнатуру select_atom(),
обернуть вызовы снаружи и пропускать повторы.

Запуск: python3 select_pilot_atoms.py [N]  (по умолчанию N=8, диапазон
пилота по SPEC.md — 5-10). Печатает в stdout JSON:
{"atoms": [...], "skip_events": [...]}
"""

import io
import os
import sys
import json
import contextlib
from datetime import datetime

import atom_selector
import graph_reader

MAX_ATTEMPTS_MULTIPLIER = 20  # защита от зацикливания, если атомов не хватает


def select_pilot_atoms(n: int) -> tuple:
    """
    Возвращает (atoms, skip_events, console_log).

    atoms: список {"cluster", "atom_path" (относительно brain/), "atom_text"}
    skip_events: список {"type": "duplicate"|"read_error"|"empty_cluster", "detail": str}
    console_log: полный текст, что atom_selector.py напечатал бы в консоль
                 (для попадания read_error/empty_cluster событий в лог пилота,
                 без изменения логики самого atom_selector.py)
    """
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
            if result["atom_path"] in seen_paths:
                print(f"[select_pilot_atoms] Пропуск дубликата: {result['atom_path']}")
                continue
            seen_paths.add(result["atom_path"])
            atoms.append({
                "cluster": result["cluster"],
                "atom_path": os.path.relpath(result["atom_path"], graph_reader.BRAIN_REPO_DIR),
                "atom_text": result["atom_text"],
            })

    console_log = captured.getvalue()
    for line in console_log.splitlines():
        if "Пропуск дубликата" in line:
            skip_events.append({"type": "duplicate", "detail": line})
        elif "Пропуск файла" in line:
            skip_events.append({"type": "read_error", "detail": line})
        elif "Пропуск кластера" in line:
            skip_events.append({"type": "empty_cluster", "detail": line})

    if len(atoms) < n:
        raise RuntimeError(
            f"select_pilot_atoms: набрано только {len(atoms)} из {n} уникальных "
            f"атомов за {attempts} попыток."
        )

    return atoms, skip_events, console_log


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    atoms, skip_events, console_log = select_pilot_atoms(n)
    sys.stderr.write(console_log)
    print(json.dumps({
        "run_timestamp": datetime.now().isoformat(),
        "atoms": atoms,
        "skip_events": skip_events,
    }, ensure_ascii=False, indent=2))
