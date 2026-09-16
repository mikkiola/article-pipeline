"""One-shot orchestration script — real end-to-end run confirming the
M4 wiring: Collector adapter -> pre-filter -> framing -> write_verdict
-> AuthoringContext -> daily_brief-shaped dict -> constructed LinkedIn
prompt (ADR-0045).

Throwaway orchestration, same class as run_pilot.py and
run_collector_pilot.py — not TDD'd for that reason.

Deliberately stops at PROMPT CONSTRUCTION, does not call
daily_linkedin_author.call_model() — that's a real, billable Anthropic
API call producing draft-quality output; not invoked without explicit
authorization to do so.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "adapters"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "author"))
import framing  # noqa: E402
import pre_filter  # noqa: E402
import write_verdict  # noqa: E402
import collector as collector_adapter  # noqa: E402
from authoring_context import build_authoring_contexts  # noqa: E402
from linkedin_verdict_reader import build_daily_brief_from_authoring_contexts  # noqa: E402
import daily_linkedin_author  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_BRIEF_PATH = REPO_ROOT.parent / "collector" / "data" / "daily_brief_2026-09-14.json"


def _restatement_framing(unit_metadata: dict) -> str:
    return (
        f"{unit_metadata['repo']}: {unit_metadata['commit_count']} commit(s), "
        f"{unit_metadata['diffstat']} lines changed today (branch: {unit_metadata['branch']})."
    )


def main() -> None:
    print(f"daily_brief source: {DAILY_BRIEF_PATH}")
    with open(DAILY_BRIEF_PATH, "r", encoding="utf-8") as f:
        daily_brief = json.load(f)

    units = collector_adapter.adapt_daily_brief(daily_brief)
    print(f"units built: {len(units)}")

    pre_filter_results = {r["claim_id"]: r for r in pre_filter.run_pre_filter(units)}
    for claim_id, result in pre_filter_results.items():
        print(f"  {claim_id}: {result['pre_filter_classification']}")

    gate_result = pre_filter.check_gate_condition(list(pre_filter_results.values()))
    print(f"gate_result: {gate_result}")

    claim_treatments = []
    for unit in units:
        pf = pre_filter_results[unit.unit_id]
        if pf["pre_filter_classification"] == "include":
            treatment = framing.build_claim_treatment(
                claim_id=unit.unit_id,
                pre_filter_classification=pf["pre_filter_classification"],
                pre_filter_reason=pf["reason"],
                framing=_restatement_framing(unit.metadata),
                derivation_kind="restatement",
                source_status_snapshot={
                    "integrity_status": unit.integrity_status,
                    "corroboration_status": unit.corroboration_status,
                },
            )
        else:
            treatment = framing.build_claim_treatment(
                claim_id=unit.unit_id,
                pre_filter_classification=pf["pre_filter_classification"],
                pre_filter_reason=pf["reason"],
            )
        claim_treatments.append(treatment)

    run_id = datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")
    verdict = write_verdict.build_verdict(run_id, gate_result, claim_treatments)
    verdict_path = write_verdict.write_outputs(run_id, verdict)
    print(f"verdict written: {verdict_path}")

    # AuthoringContext built here, in-process, from the SAME units +
    # claim_treatments this run already has in memory — not re-derived
    # from the persisted verdict file (see authoring_context.py's
    # docstring for why that wouldn't have enough data).
    contexts = build_authoring_contexts(units, claim_treatments)
    print(f"\nAuthoringContext entries: {len(contexts)}")
    for ctx in contexts:
        print(f"  {ctx.claim_id}: source_type={ctx.source_type} commit_messages={ctx.commit_messages}")

    daily_brief_shaped = build_daily_brief_from_authoring_contexts(
        contexts, date=daily_brief["date"]
    )
    print("\n=== reconstructed daily_brief-shaped dict ===")
    print(json.dumps(daily_brief_shaped, ensure_ascii=False, indent=2))

    prompt = daily_linkedin_author.build_prompt(daily_brief_shaped)
    print(f"\n=== constructed prompt (mode={daily_brief_shaped['mode']}), length={len(prompt)} chars ===")
    print(prompt)


if __name__ == "__main__":
    main()
