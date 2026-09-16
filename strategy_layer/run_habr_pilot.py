"""One-shot orchestration script — real end-to-end run confirming M5's
wiring: Collector adapter -> pre-filter -> framing -> write_verdict ->
AuthoringContext -> per-claim language-check -> HabrDigest (ADR-0046)
-> rendered Habr Markdown.

Throwaway orchestration, same class as run_pilot.py/
run_collector_pilot.py/run_linkedin_pilot.py — not TDD'd for that
reason.

Framing text here is deliberately written in Russian at the source,
not translated after the fact — matches decide_framing()'s own
documented instruction ("Habr-bound framing must be written in
Russian"), and lets this real run actually exercise looks_russian()'s
safety net on real (passing) text rather than only proving it via
synthetic English fixtures in the unit tests.
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
from habr_verdict_to_story import build_habr_digest  # noqa: E402
from habr_weekly_author import render_habr_digest  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT.parent / "collector" / "data" / "manifest_2026-09-12.json"


def _restatement_framing_russian(unit_metadata: dict) -> str:
    return (
        f"В репозитории {unit_metadata['repo']} было "
        f"{unit_metadata['commit_count']} коммит(ов) за последние "
        f"{unit_metadata['window_days']} дней (ветка: {unit_metadata['branch']})."
    )


def main() -> None:
    print(f"manifest source: {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    units = collector_adapter.adapt_manifest(manifest)
    print(f"units built: {len(units)}")

    pre_filter_results = {r["claim_id"]: r for r in pre_filter.run_pre_filter(units)}
    included = [cid for cid, r in pre_filter_results.items() if r["pre_filter_classification"] == "include"]
    print(f"pre-filter 'include': {len(included)} -> {included}")

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
                framing=_restatement_framing_russian(unit.metadata),
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

    contexts = build_authoring_contexts(units, claim_treatments)
    print(f"\nAuthoringContext entries: {len(contexts)}")
    for ctx in contexts:
        print(f"  {ctx.claim_id}: framing={ctx.framing!r}")

    # ADR-0046: multi-claim is now the supported case, not a refused
    # one — build_habr_digest() represents every real included claim
    # this run actually has, not a single arbitrarily-chosen one.
    digest = build_habr_digest(contexts)
    print(f"\nHabrDigest sections: {len(digest.sections)} (of {len(contexts)} included contexts)")

    draft = render_habr_digest(digest)
    print(f"\n=== rendered Habr draft ({len(draft)} chars) ===")
    print(draft)


if __name__ == "__main__":
    main()
