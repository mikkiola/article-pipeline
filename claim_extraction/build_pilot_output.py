"""
Сборка финальных артефактов пилота Claim Extraction из результатов отбора
атомов (select_pilot_atoms.py) и извлечённых Claim-записей.

Извлечение Claim/no_claim выполняется интерактивно Claude Code (SPEC.md) —
не этим скриптом. Этот скрипт только:
  - проставляет claim_id/extracted_at,
  - собирает pilot_run_<run_id>.json (только поля по схеме SPEC.md — служебное
    поле context_insufficiency в финальный артефакт не попадает),
  - собирает pilot_log_<run_id>.json: события отбора, счётчики категорий
    D-009, проверку Reversal condition D-013 (порог 40%),
  - никогда не перезаписывает файлы предыдущих прогонов (Immutable Lineage,
    D-011) — новый прогон всегда получает новое имя файла по run_id.

Запуск:
    python3 build_pilot_output.py <selection.json> <claims.json>

<selection.json> — вывод select_pilot_atoms.py (run_timestamp, atoms, skip_events)
<claims.json>    — список Claim/no_claim записей (см. pilot_claims.json), по
                   одной записи на атом, в том же порядке, что atoms
                   в selection.json.
"""

import os
import sys
import json
from datetime import datetime

REVERSAL_THRESHOLD = 0.4  # D-013: >=40% атомов с нехваткой контекста

SCHEMA_FIELDS = [
    "novelty", "basis", "audience", "belief_changed", "desired_action",
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def build(selection_path: str, claims_path: str) -> tuple:
    with open(selection_path, "r", encoding="utf-8") as f:
        selection = json.load(f)
    with open(claims_path, "r", encoding="utf-8") as f:
        claims_raw = json.load(f)

    atoms = selection["atoms"]
    if len(atoms) != len(claims_raw):
        raise ValueError(
            f"Число атомов ({len(atoms)}) не совпадает с числом Claim-записей "
            f"({len(claims_raw)}) — проверь соответствие claims.json selection.json."
        )

    run_dt = datetime.fromisoformat(selection["run_timestamp"])
    run_id = run_dt.strftime("%Y%m%dT%H%M%S")

    pilot_run = []
    category_counts = {"no_claim": 0, "wrong_framing": 0, "bad_evidence": 0, "technical_failure": 0}
    context_insufficiency_count = 0
    context_insufficiency_atoms = []

    for i, (atom, record) in enumerate(zip(atoms, claims_raw), start=1):
        if atom["atom_path"] != record["atom_path"]:
            raise ValueError(
                f"Порядок атомов не совпадает на позиции {i}: "
                f"{atom['atom_path']} != {record['atom_path']}"
            )

        entry = {
            "claim_id": f"{run_id}_{i:02d}",
            "extracted_at": selection["run_timestamp"],
            "atom_path": record["atom_path"],
            "status": record["status"],
            "confidence": record["confidence"],
            "category": record["category"],
            "reason": record["reason"],
        }
        for field in SCHEMA_FIELDS:
            entry[field] = record[field]
        pilot_run.append(entry)

        if record["category"] in category_counts:
            category_counts[record["category"]] += 1

        if record.get("context_insufficiency"):
            context_insufficiency_count += 1
            context_insufficiency_atoms.append(record["atom_path"])

    # technical_failure — атомы, не дошедшие до извлечения (read_error на этапе отбора)
    read_error_events = [e for e in selection["skip_events"] if e["type"] == "read_error"]
    category_counts["technical_failure"] += len(read_error_events)

    total_atoms = len(atoms)
    context_fraction = context_insufficiency_count / total_atoms if total_atoms else 0.0
    reversal_triggered = context_fraction >= REVERSAL_THRESHOLD

    pilot_log = {
        "run_id": run_id,
        "run_timestamp": selection["run_timestamp"],
        "total_atoms": total_atoms,
        "skip_events": selection["skip_events"],
        "category_counts": category_counts,
        "d013_reversal_check": {
            "threshold": REVERSAL_THRESHOLD,
            "context_insufficiency_count": context_insufficiency_count,
            "context_insufficiency_fraction": round(context_fraction, 4),
            "context_insufficiency_atoms": context_insufficiency_atoms,
            "reversal_condition_triggered": reversal_triggered,
        },
    }

    return run_id, pilot_run, pilot_log


def write_outputs(run_id: str, pilot_run: list, pilot_log: dict) -> tuple:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run_path = os.path.join(OUTPUT_DIR, f"pilot_run_{run_id}.json")
    log_path = os.path.join(OUTPUT_DIR, f"pilot_log_{run_id}.json")

    for path in (run_path, log_path):
        if os.path.exists(path):
            raise FileExistsError(
                f"{path} уже существует — Immutable Lineage (D-011) запрещает "
                f"перезапись прежнего прогона."
            )

    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(pilot_run, f, ensure_ascii=False, indent=2)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(pilot_log, f, ensure_ascii=False, indent=2)

    return run_path, log_path


if __name__ == "__main__":
    selection_path, claims_path = sys.argv[1], sys.argv[2]
    run_id, pilot_run, pilot_log = build(selection_path, claims_path)
    run_path, log_path = write_outputs(run_id, pilot_run, pilot_log)
    print(f"pilot_run: {run_path}")
    print(f"pilot_log: {log_path}")
    print(f"reversal_condition_triggered: {pilot_log['d013_reversal_check']['reversal_condition_triggered']}")
