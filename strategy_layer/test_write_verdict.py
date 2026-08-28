"""Tests for strategy_layer/write_verdict.py (SPEC.md Data Model,
Non-Functional Requirement #3, Milestone M4).

No RED-first TDD here (see the M4 commit message for the judgment
call): the collision check is a single, structurally trivial condition
(`if os.path.exists(path): raise`) directly adapted from an already-
working precedent (evidence_package/write_evidence.py,
claim_extraction/build_pilot_output.py), not a mechanism with subtle
trigger conditions the way M2's gate or M3's override direction logic
were.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import framing  # noqa: E402
import write_verdict  # noqa: E402


def make_claim_treatments() -> list[dict]:
    return [
        framing.build_claim_treatment(
            claim_id="c1",
            pre_filter_classification="exclude",
            pre_filter_reason="No evidence found; accuracy not established.",
        ),
        framing.build_claim_treatment(
            claim_id="c2",
            pre_filter_classification="exclude",
            pre_filter_reason="No evidence found; accuracy not established.",
            final_classification="include",
            framing="Reported as a live, honestly-labeled open question.",
            override_reason="Strong corroborating context.wiki_links.",
        ),
    ]


def test_build_verdict_assembles_schema_and_derives_overrides():
    claim_treatments = make_claim_treatments()
    gate_result = {"status": "gated", "gates": {"all_claims_unverifiable": True}}

    verdict = write_verdict.build_verdict("run1", gate_result, claim_treatments)

    assert verdict["run_id"] == "run1"
    assert verdict["status"] == "gated"
    assert verdict["gates"] == {"all_claims_unverifiable": True}
    assert verdict["claim_treatments"] == claim_treatments
    assert verdict["overrides"] == [
        {
            "claim_id": "c2",
            "pre_filter_classification": "exclude",
            "final_classification": "include",
            "reason": "Strong corroborating context.wiki_links.",
        }
    ]
    assert verdict["created_at"]


def test_build_verdict_overrides_empty_when_no_overrides():
    claim_treatments = [
        framing.build_claim_treatment(
            claim_id="c1",
            pre_filter_classification="include",
            pre_filter_reason=None,
            framing="Bare include, no override.",
        ),
    ]
    gate_result = {"status": "normal", "gates": {"all_claims_unverifiable": False}}

    verdict = write_verdict.build_verdict("run2", gate_result, claim_treatments)

    assert verdict["overrides"] == []


def test_write_outputs_writes_verdict_file(tmp_path, monkeypatch):
    monkeypatch.setattr(write_verdict, "OUTPUT_DIR", str(tmp_path))
    verdict = write_verdict.build_verdict(
        "run3",
        {"status": "normal", "gates": {"all_claims_unverifiable": False}},
        make_claim_treatments(),
    )

    path = write_verdict.write_outputs("run3", verdict)

    assert path == str(tmp_path / "verdict_run3.json")
    with open(path, "r", encoding="utf-8") as f:
        written = json.load(f)
    assert written == verdict


def test_write_outputs_raises_on_run_id_collision_and_preserves_first_file(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(write_verdict, "OUTPUT_DIR", str(tmp_path))
    first_verdict = write_verdict.build_verdict(
        "run4",
        {"status": "normal", "gates": {"all_claims_unverifiable": False}},
        make_claim_treatments(),
    )
    path = write_verdict.write_outputs("run4", first_verdict)
    original_bytes = Path(path).read_bytes()

    second_verdict = write_verdict.build_verdict(
        "run4",
        {"status": "gated", "gates": {"all_claims_unverifiable": True}},
        [],
    )

    with pytest.raises(FileExistsError):
        write_verdict.write_outputs("run4", second_verdict)

    assert Path(path).read_bytes() == original_bytes
