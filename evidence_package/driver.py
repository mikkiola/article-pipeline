"""Driver script for the Evidence Package pilot — search phase (SPEC.md, M3).

Reads Claims with status "claim" from the most recent
claim_extraction/output/pilot_run_*.json, builds one search query per
Claim, and calls search_backend.search() under a hard request budget.

Out of scope for this script (see SPEC.md):
  - Assigning status/source_url/license/note per Claim is an
    interactive Claude Code judgment call (M4), not automated here —
    except the network-error and budget-exhausted cases below, which
    SPEC.md fixes as automatic outcomes regardless of interactive
    review.
  - Writing evidence_run_*.json / evidence_log_*.json (M5, Immutable
    Lineage) — this script returns in-memory records only.

MAX_REQUESTS_PER_CLAIM is the ceiling SPEC.md allows per Claim across
both this script and any interactive retry — SPEC.md is explicit that
the second attempt only happens if the first result isn't relevant
enough, judged by the interactive M4 session, not automatically here.
This script itself only ever makes the first attempt, so on its own it
never exceeds one request per Claim.
"""

from __future__ import annotations

import glob
import json
import os
import re
from datetime import datetime, timezone

from search_backend import search as linkup_search

MAX_REQUESTS_PER_CLAIM = 2  # SPEC.md: "до 2 раз на Claim"
MAX_REQUESTS_PER_RUN = 20  # SPEC.md: "жёсткий лимит на весь прогон — 20 запросов"


class SearchBudgetError(RuntimeError):
    """Raised when a retry would exceed the per-Claim or run-wide budget."""

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CLAIM_EXTRACTION_OUTPUT_DIR = os.path.join(_THIS_DIR, "..", "claim_extraction", "output")

_PILOT_RUN_RE = re.compile(r"^pilot_run_(\d{8}T\d{6})\.json$")


def find_latest_pilot_run(output_dir: str = CLAIM_EXTRACTION_OUTPUT_DIR) -> str:
    candidates = []
    for path in glob.glob(os.path.join(output_dir, "pilot_run_*.json")):
        match = _PILOT_RUN_RE.match(os.path.basename(path))
        if match:
            candidates.append((match.group(1), path))
    if not candidates:
        raise FileNotFoundError(f"No pilot_run_*.json found in {output_dir}")
    candidates.sort(key=lambda pair: pair[0])
    return candidates[-1][1]


def load_claims(pilot_run_path: str, limit: int = 10) -> list[dict]:
    with open(pilot_run_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    return [r for r in records if r.get("status") == "claim"][:limit]


def build_search_query(claim: dict) -> str:
    return f"{claim['novelty']['value']} {claim['basis']['value']}"


def run_searches(
    claims: list[dict],
    search_fn=linkup_search,
    max_requests_per_run: int = MAX_REQUESTS_PER_RUN,
) -> tuple[list[dict], dict]:
    """Run one search attempt per Claim under the run-wide budget.

    Returns (records, log_summary). `records` carries one dict per
    Claim with `status` left as None when a search succeeded (awaiting
    M4's interactive assessment), or preset to "unverifiable" /
    "pending" for the two automatic outcomes SPEC.md defines.
    """
    records = []
    events = []
    requests_used_total = 0
    budget_exhausted = False

    for claim in claims:
        claim_id = claim["claim_id"]
        query = build_search_query(claim)

        if requests_used_total >= max_requests_per_run:
            budget_exhausted = True
            records.append({
                "claim_id": claim_id,
                "search_query": query,
                "requests_used": 0,
                "search_results": None,
                "status": "pending",
                "note": None,
                "searched_at": None,
            })
            continue

        searched_at = datetime.now(timezone.utc).astimezone().isoformat()
        try:
            results = search_fn(query)
        except Exception as exc:
            # Broad catch is deliberate here: this is the external network
            # boundary SPEC.md requires resilience against ("любая сетевая
            # ошибка/таймаут... не должна ронять весь прогон"), and the
            # linkup-sdk error classes share no common base to narrow on.
            requests_used_total += 1
            error_text = f"{type(exc).__name__}: {exc}"
            events.append({
                "type": "search_error",
                "claim_id": claim_id,
                "error": error_text,
                "at": searched_at,
            })
            records.append({
                "claim_id": claim_id,
                "search_query": query,
                "requests_used": 1,
                "search_results": None,
                "status": "unverifiable",
                "note": f"Сетевая ошибка/таймаут Linkup: {error_text}",
                "searched_at": searched_at,
            })
            continue

        requests_used_total += 1
        records.append({
            "claim_id": claim_id,
            "search_query": query,
            "requests_used": 1,
            "search_results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
            ],
            "status": None,
            "note": None,
            "searched_at": searched_at,
        })

    if budget_exhausted:
        events.append({"type": "budget_exhausted", "requests_used_total": requests_used_total})

    log_summary = {
        "requests_used_total": requests_used_total,
        "search_budget_exhausted": budget_exhausted,
        "events": events,
    }
    return records, log_summary


def retry_search(
    record: dict,
    requests_used_total: int,
    search_fn=linkup_search,
    max_requests_per_claim: int = MAX_REQUESTS_PER_CLAIM,
    max_requests_per_run: int = MAX_REQUESTS_PER_RUN,
) -> dict:
    """Make a second search attempt for one Claim (interactive M4 call only).

    Enforces both budgets as hard checks, not just the declared
    constants: raises SearchBudgetError instead of silently exceeding
    either cap. Mutates and returns `record` — appends the new results,
    bumps `requests_used`, updates `searched_at`. Does not touch
    run-wide bookkeeping beyond validating against the caller-supplied
    `requests_used_total`; the caller (M4 session) is responsible for
    tracking that total across all Claims in the run.
    """
    if record["requests_used"] >= max_requests_per_claim:
        raise SearchBudgetError(
            f"{record['claim_id']}: per-Claim budget exhausted "
            f"({record['requests_used']}/{max_requests_per_claim})"
        )
    if requests_used_total >= max_requests_per_run:
        raise SearchBudgetError(
            f"{record['claim_id']}: run-wide budget exhausted "
            f"({requests_used_total}/{max_requests_per_run})"
        )

    results = search_fn(record["search_query"])
    record["requests_used"] += 1
    record["search_results"] = (record["search_results"] or []) + [
        {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
    ]
    record["searched_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    return record


def main() -> None:
    pilot_run_path = find_latest_pilot_run()
    claims = load_claims(pilot_run_path)
    print(f"pilot_run source: {pilot_run_path}")
    print(f"claims loaded: {len(claims)}")
    records, log_summary = run_searches(claims)
    for record in records:
        result_count = len(record["search_results"]) if record["search_results"] else 0
        print(
            f"{record['claim_id']}: requests_used={record['requests_used']} "
            f"status={record['status']} results={result_count}"
        )
    print(
        f"requests_used_total={log_summary['requests_used_total']} "
        f"search_budget_exhausted={log_summary['search_budget_exhausted']}"
    )


if __name__ == "__main__":
    main()
