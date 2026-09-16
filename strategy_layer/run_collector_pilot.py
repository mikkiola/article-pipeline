"""One-shot orchestration script — Strategy Layer's real-data validation
run against Collector's adapter (SPEC.md's source-independence
extension, Milestone M3 real-data run).

Throwaway orchestration, same class as run_pilot.py and
evidence_package/driver.py: no reusable library logic lives here, only
wiring — not TDD'd for that reason, same judgment as those scripts.

Framing text here is template-generated, not individually authored —
deliberately, and only because every included unit's derivation_kind
is "restatement" (Collector's raw telemetry: bare commit/diffstat
counts, no evaluation or causal claim). "restatement" is definitionally
just re-describing a record's own fields, which doesn't require the
same interactive judgment call an "evaluation" or "causal_claim"
framing would (see strategy_layer/framing.py's decide_framing()
docstring) — a template is an honest restatement, not a shortcut
around real judgment.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "adapters"))
import framing  # noqa: E402
import pre_filter  # noqa: E402
import write_verdict  # noqa: E402
import collector as collector_adapter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT.parent / "collector" / "data" / "manifest_2026-09-12.json"


def _restatement_framing(unit_metadata: dict) -> str:
    return (
        f"{unit_metadata['repo']}: {unit_metadata['commit_count']} commit(s), "
        f"{unit_metadata['diffstat'] if 'diffstat' in unit_metadata else unit_metadata.get('counts')} "
        f"in the last {unit_metadata['window_days']} day(s) "
        f"(branch: {unit_metadata['branch']})."
    )


def main() -> None:
    print(f"manifest source: {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    units = collector_adapter.adapt_manifest(manifest)
    print(f"units built: {len(units)}")
    for unit in units:
        print(
            f"  {unit.unit_id}: integrity_status={unit.integrity_status} "
            f"({unit.metadata['integrity_check_detail']})"
        )

    pre_filter_results = {r["claim_id"]: r for r in pre_filter.run_pre_filter(units)}
    for claim_id, result in pre_filter_results.items():
        print(f"  {claim_id}: pre_filter_classification={result['pre_filter_classification']}")

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

    print("\n=== verdict ===")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))

    verdict_path = write_verdict.write_outputs(run_id, verdict)
    print(f"\nverdict written: {verdict_path}")


if __name__ == "__main__":
    main()
