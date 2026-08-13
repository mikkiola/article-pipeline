"""Write evidence_run/evidence_log (M5, Immutable Lineage, SPEC.md).

Takes Evidence records already assessed interactively (status/
source_url/source_title/license/note assigned in M4 — this module
does not assign them) and writes the two canonical output files.

Never overwrites a previous run: a run_id collision (same timestamp)
raises FileExistsError instead of silently overwriting, the same
precedent as claim_extraction/build_pilot_output.py.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

STATUSES = ("verified", "disputed", "unverifiable", "pending")


def build_evidence_run(run_id: str, assessed: list[dict]) -> list[dict]:
    created_at = datetime.now(timezone.utc).astimezone().isoformat()
    evidence_run = []
    for i, item in enumerate(assessed, start=1):
        if item["status"] not in STATUSES:
            raise ValueError(f"{item['claim_id']}: недопустимый status '{item['status']}'")
        evidence_run.append({
            "evidence_id": f"{run_id}_{i:02d}",
            "run_id": run_id,
            "created_at": created_at,
            "claim_id": item["claim_id"],
            "status": item["status"],
            "searched_at": item["searched_at"],
            "search_query": item["search_query"],
            "requests_used": item["requests_used"],
            "source_url": item["source_url"],
            "source_title": item["source_title"],
            "license": item["license"],
            "note": item["note"],
        })
    return evidence_run


def build_evidence_log(run_id: str, evidence_run: list[dict], search_log_summary: dict) -> dict:
    status_counts = {status: 0 for status in STATUSES}
    for record in evidence_run:
        status_counts[record["status"]] += 1
    return {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "total_claims": len(evidence_run),
        "status_counts": status_counts,
        "requests_used_total": search_log_summary["requests_used_total"],
        "search_budget_exhausted": search_log_summary["search_budget_exhausted"],
        "events": search_log_summary["events"],
    }


def write_outputs(run_id: str, evidence_run: list[dict], evidence_log: dict) -> tuple[str, str]:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run_path = os.path.join(OUTPUT_DIR, f"evidence_run_{run_id}.json")
    log_path = os.path.join(OUTPUT_DIR, f"evidence_log_{run_id}.json")

    for path in (run_path, log_path):
        if os.path.exists(path):
            raise FileExistsError(
                f"{path} уже существует — Immutable Lineage запрещает "
                f"перезапись прежнего прогона."
            )

    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(evidence_run, f, ensure_ascii=False, indent=2)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(evidence_log, f, ensure_ascii=False, indent=2)

    return run_path, log_path
