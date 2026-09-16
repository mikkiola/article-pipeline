"""Synthetic alien-source contract test (SPEC.md M6, ADR-0048's Anti-
Corruption Layer boundary).

Proves R3 ("adding a new source changes only its own adapter") by
construction: builds a CanonicalUnit shaped like a source neither
pre_filter.py, framing.py, nor write_verdict.py has ever been written
against, and confirms all three process it end-to-end with zero
special-casing.

`CanonicalUnit.source` is `Literal["brain", "collector"]` — kept
strict, symmetric with every other field's strictness (extra="forbid",
frozen=True). A literal third Literal value ("source_x") would be
rejected at construction by Pydantic itself, which would prove nothing
about strategy_layer/'s own genericity. Per SPEC.md's own fallback for
exactly this case: this test instead uses a structurally valid
`source="collector"` tag carrying a semantically alien `unit_id` and
`metadata` shape no real Collector adapter would ever produce (a
fictitious "weather-satellite-telemetry" source) — the discriminator
the core logic is actually forbidden from reading is `metadata`'s
content and `unit_id`'s naming, not the `source` literal itself, and
this is exactly what the test exercises.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import CanonicalUnit  # noqa: E402
import pre_filter  # noqa: E402
import framing  # noqa: E402
import write_verdict  # noqa: E402

ALIEN_UNIT_ID = "weather-satellite-telemetry::orbit-4471::pass-9"
ALIEN_METADATA = {
    "telescope_array": "alpha-7",
    "orbital_pass_id": "pass-9",
    "signal_to_noise_db": 41.2,
    "instrument_calibration_ref": "cal-2026-09-01",
}


def _alien_unit(**overrides) -> CanonicalUnit:
    base = dict(
        unit_id=ALIEN_UNIT_ID,
        source="collector",
        created_at="2026-09-16T00:00:00+00:00",
        integrity_status="valid",
        integrity_check_method="orbital_pass_signal_reconciliation",
        corroboration_status="not_applicable",
        assertion_text=None,
        metadata=ALIEN_METADATA,
    )
    base.update(overrides)
    return CanonicalUnit(**base)


def test_alien_unit_valid_not_applicable_classifies_include():
    unit = _alien_unit()
    result = pre_filter.classify_unit(unit)
    assert result["pre_filter_classification"] == "include"
    assert result["claim_id"] == ALIEN_UNIT_ID


def test_alien_unit_invalid_integrity_classifies_exclude_regardless_of_metadata():
    unit = _alien_unit(integrity_status="invalid")
    result = pre_filter.classify_unit(unit)
    assert result["pre_filter_classification"] == "exclude"
    assert "invalid" in result["reason"]


def test_alien_unit_corroborated_requires_source_url_and_license():
    unit = _alien_unit(
        corroboration_status="corroborated",
        assertion_text="Orbital pass 9 detected a 3.1C anomaly.",
        source_url="https://example-observatory.test/pass-9",
        license="CC-BY-4.0",
    )
    result = pre_filter.classify_unit(unit)
    assert result["pre_filter_classification"] == "include"


def test_alien_unit_flows_through_framing_with_no_special_casing():
    unit = _alien_unit()
    pre_filter_result = pre_filter.classify_unit(unit)
    treatment = framing.build_claim_treatment(
        claim_id=pre_filter_result["claim_id"],
        pre_filter_classification=pre_filter_result["pre_filter_classification"],
        pre_filter_reason=pre_filter_result["reason"],
        framing="Orbital pass 9 recorded a routine telemetry reading.",
        derivation_kind="restatement",
        source_status_snapshot={
            "integrity_status": unit.integrity_status,
            "corroboration_status": unit.corroboration_status,
        },
    )
    assert treatment["claim_id"] == ALIEN_UNIT_ID
    assert treatment["final_classification"] == "include"
    assert treatment["framing"] is not None


def test_alien_unit_flows_through_full_verdict_assembly(tmp_path, monkeypatch):
    monkeypatch.setattr(write_verdict, "OUTPUT_DIR", str(tmp_path))

    unit = _alien_unit()
    pre_filter_result = pre_filter.classify_unit(unit)
    gate_result = pre_filter.check_gate_condition([pre_filter_result])
    treatment = framing.build_claim_treatment(
        claim_id=pre_filter_result["claim_id"],
        pre_filter_classification=pre_filter_result["pre_filter_classification"],
        pre_filter_reason=pre_filter_result["reason"],
        framing="Orbital pass 9 recorded a routine telemetry reading.",
    )
    verdict = write_verdict.build_verdict(
        "test_alien_run", gate_result, [treatment]
    )
    path = write_verdict.write_outputs("test_alien_run", verdict)

    assert Path(path).exists()
    assert verdict["status"] == "normal"
    assert verdict["claim_treatments"][0]["claim_id"] == ALIEN_UNIT_ID


def test_no_source_specific_branching_exists_in_core_files():
    """Static confirmation, not just behavioral: none of the three core
    files reference this test's alien source shape by name anywhere —
    genericity isn't merely observed to work today, nothing in the
    source text could have special-cased it."""
    core_files = [
        Path(pre_filter.__file__),
        Path(framing.__file__),
        Path(write_verdict.__file__),
    ]
    for f in core_files:
        text = f.read_text(encoding="utf-8")
        assert "weather-satellite" not in text
        assert "orbital_pass" not in text
