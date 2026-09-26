"""Tests for linkedin_publisher/daily_publish.py's extracted, testable
functions — resolve_daily_brief_path(), build_content_id(),
pick_representative_claim_id(), build_block_record(), build_pass_record().

main() itself is thin I/O + network wiring (read a file, call already-
tested library functions, write a record) — not exhaustively tested
end-to-end here, matching this project's own established judgment for
driver/orchestration scripts (strategy_layer/run_pilot.py,
evidence_package/driver.py: "no reusable library logic... not TDD'd for
that reason"). What IS reusable, gating logic — the functions below —
is tested.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_publish  # noqa: E402


# --- resolve_daily_brief_path --------------------------------------------


def test_resolve_daily_brief_path_prefers_explicit_path():
    result = daily_publish.resolve_daily_brief_path(explicit_path="/some/explicit/path.json")
    assert result == Path("/some/explicit/path.json")


def test_resolve_daily_brief_path_defaults_to_workspace_root_and_date():
    result = daily_publish.resolve_daily_brief_path(
        workspace_root=Path("/workspace"), date="2026-09-24"
    )
    assert result == Path("/workspace/collector/data/daily_brief_2026-09-24.json")


# --- build_content_id -----------------------------------------------------


def test_build_content_id_is_date_keyed_not_wall_clock():
    assert daily_publish.build_content_id("2026-09-24") == "linkedin-2026-09-24"
    # Same date called twice (a retry) must produce the identical id.
    assert daily_publish.build_content_id("2026-09-24") == daily_publish.build_content_id("2026-09-24")


# --- pick_representative_claim_id -----------------------------------------


def test_pick_representative_claim_id_returns_first():
    assert daily_publish.pick_representative_claim_id(["c1", "c2", "c3"]) == "c1"


def test_pick_representative_claim_id_raises_on_empty_list():
    with pytest.raises(ValueError, match="empty unit list"):
        daily_publish.pick_representative_claim_id([])


# --- build_block_record ----------------------------------------------------


def test_build_block_record_shape():
    now = datetime(2026, 9, 24, 9, 0, 0, tzinfo=timezone.utc)
    pre_filter_results = [
        {"claim_id": "c1", "pre_filter_classification": "exclude", "reason": "No evidence found."},
        {"claim_id": "c2", "pre_filter_classification": "exclude", "reason": "Not yet resolved."},
    ]

    record = daily_publish.build_block_record("linkedin-2026-09-24", pre_filter_results, now)

    assert record.content_id == "linkedin-2026-09-24"
    assert record.platform == "linkedin"
    assert record.claim_id == "c1"
    assert record.gate_policy == "bootstrap"
    assert record.gate_status == "block"
    assert "c1" in record.block_reason
    assert "No evidence found." in record.block_reason
    assert "2/2 excluded" in record.block_reason
    assert record.published_at == now
    assert record.gate_evaluated_at == now


def test_build_block_record_raises_on_empty_results():
    with pytest.raises(ValueError):
        daily_publish.build_block_record("linkedin-2026-09-24", [], datetime.now(timezone.utc))


# --- build_pass_record -----------------------------------------------------


def test_build_pass_record_shape():
    now = datetime(2026, 9, 24, 9, 0, 0, tzinfo=timezone.utc)

    record = daily_publish.build_pass_record(
        "linkedin-2026-09-24", "https://www.linkedin.com/feed/update/123/", "c1", now
    )

    assert record.content_id == "linkedin-2026-09-24"
    assert record.platform == "linkedin"
    assert record.url == "https://www.linkedin.com/feed/update/123/"
    assert record.claim_id == "c1"
    assert record.gate_policy == "bootstrap"
    assert record.gate_status == "pass"
    assert record.block_reason is None


# --- main(): read-before-publish Registry guard ---------------------------
#
# Exercises main() against a real Registry directory (tmp_path) with every
# network/LLM boundary mocked. The regression these cover: two workflow
# runs both published for content_id linkedin-2026-09-24 because nothing
# read the Registry before publish_post() was called.

_CONTENT_ID = "linkedin-2026-09-24"
_POST_URL = "https://www.linkedin.com/feed/update/urn:li:share:1/"


def _pass_record():
    now = datetime(2026, 9, 24, 7, 0, 0, tzinfo=timezone.utc)
    return daily_publish.build_pass_record(_CONTENT_ID, _POST_URL, "u1", now)


def _block_record():
    now = datetime(2026, 9, 24, 7, 0, 0, tzinfo=timezone.utc)
    return daily_publish.build_block_record(
        _CONTENT_ID,
        [{"claim_id": "u1", "pre_filter_classification": "exclude", "reason": "No evidence."}],
        now,
    )


def _setup_main(monkeypatch, tmp_path):
    """Redirects the Registry to tmp_path/registry and mocks everything
    outside it, without running main(). Returns the dict of mocks so
    tests can assert what was and wasn't called."""
    registry_dir = tmp_path / "registry"
    monkeypatch.setattr(daily_publish.registry_writer, "OUTPUT_DIR", str(registry_dir))

    brief_path = tmp_path / "daily_brief_2026-09-24.json"
    brief_path.write_text(json.dumps({"date": "2026-09-24"}), encoding="utf-8")
    monkeypatch.setattr(
        daily_publish,
        "parse_args",
        lambda: argparse.Namespace(daily_brief_path=str(brief_path)),
    )

    unit = SimpleNamespace(
        unit_id="u1",
        integrity_status="valid",
        corroboration_status="not_applicable",
        metadata={"repo": "r", "commit_count": 1, "diffstat": 10, "branch": "main"},
    )
    mocks = {
        "publish_post": mock.Mock(return_value=_POST_URL),
        "call_model": mock.Mock(return_value={"post": "post text"}),
        "write_outputs": mock.Mock(return_value="verdict.json"),
    }
    monkeypatch.setattr(daily_publish, "check_safety_pause_state", lambda: daily_publish.SafetyPauseState.CLOSED)
    monkeypatch.setattr(daily_publish.linkedin_client, "check_token_preflight", lambda: None)
    monkeypatch.setattr(daily_publish.linkedin_client, "publish_post", mocks["publish_post"])
    monkeypatch.setattr(daily_publish.collector_adapter, "adapt_daily_brief", lambda brief: [unit])
    monkeypatch.setattr(
        daily_publish.pre_filter,
        "run_pre_filter",
        lambda units: [{"claim_id": "u1", "pre_filter_classification": "include", "reason": "ok"}],
    )
    monkeypatch.setattr(
        daily_publish.pre_filter,
        "check_gate_condition",
        lambda results: {"status": "normal", "gates": {"zero_included_units": False}},
    )
    monkeypatch.setattr(daily_publish.framing, "build_claim_treatment", lambda **kwargs: "treatment")
    monkeypatch.setattr(daily_publish.write_verdict, "build_verdict", lambda *a, **k: "verdict")
    monkeypatch.setattr(daily_publish.write_verdict, "write_outputs", mocks["write_outputs"])
    monkeypatch.setattr(
        daily_publish, "build_authoring_contexts", lambda units, treatments: [SimpleNamespace(claim_id="u1")]
    )
    monkeypatch.setattr(
        daily_publish,
        "build_daily_brief_from_authoring_contexts",
        lambda contexts, date: {"mode": "fact"},
    )
    monkeypatch.setattr(daily_publish.daily_linkedin_author, "build_prompt", lambda brief: "prompt")
    monkeypatch.setattr(daily_publish.daily_linkedin_author, "call_model", mocks["call_model"])
    monkeypatch.setattr(
        daily_publish.daily_linkedin_author,
        "validate_structured_response",
        lambda response, mode, daily_brief=None: None,
    )

    return mocks


def _run_main(monkeypatch, tmp_path):
    mocks = _setup_main(monkeypatch, tmp_path)
    daily_publish.main()
    return mocks, tmp_path / "registry"


def test_main_skips_when_pass_record_exists(monkeypatch, tmp_path, capsys):
    registry_dir = tmp_path / "registry"
    monkeypatch.setattr(daily_publish.registry_writer, "OUTPUT_DIR", str(registry_dir))
    daily_publish.registry_writer.write_record(_pass_record())
    record_file = registry_dir / f"{_CONTENT_ID}.json"
    original_bytes = record_file.read_bytes()

    mocks, _ = _run_main(monkeypatch, tmp_path)

    mocks["publish_post"].assert_not_called()
    mocks["call_model"].assert_not_called()
    mocks["write_outputs"].assert_not_called()
    assert (
        f"Registry already has a published record for {_CONTENT_ID} — skipping, "
        f"no publish attempted."
    ) in capsys.readouterr().out
    assert record_file.read_bytes() == original_bytes


def _unit(unit_id, integrity_status, metadata):
    return SimpleNamespace(
        unit_id=unit_id,
        integrity_status=integrity_status,
        corroboration_status="not_applicable",
        metadata=metadata,
    )


def _gated_run(monkeypatch, tmp_path, units):
    mocks = _setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(daily_publish.collector_adapter, "adapt_daily_brief", lambda brief: units)
    monkeypatch.setattr(
        daily_publish.pre_filter,
        "run_pre_filter",
        lambda us: [
            {"claim_id": u.unit_id, "pre_filter_classification": "exclude", "reason": "excluded"}
            for u in us
        ],
    )
    monkeypatch.setattr(
        daily_publish.pre_filter,
        "check_gate_condition",
        lambda results: {"status": "gated", "gates": {"zero_included_units": True}},
    )
    daily_publish.main()
    return mocks


def test_main_prints_per_unit_integrity_detail_after_the_gate_result(monkeypatch, tmp_path, capsys):
    units = [
        _unit("u1", "invalid", {"repo": "archi-kg", "integrity_check_detail": "compare 404: sha not found"}),
        _unit("u2", "valid", {"repo": "collector", "integrity_check_detail": "identical"}),
    ]

    mocks = _gated_run(monkeypatch, tmp_path, units)

    out = capsys.readouterr().out
    assert "units built: 2" in out
    assert "gate_result: {'status': 'gated', 'gates': {'zero_included_units': True}}" in out
    assert "  archi-kg: integrity_status=invalid detail=compare 404: sha not found" in out
    assert "  collector: integrity_status=valid detail=identical" in out
    assert out.index("gate_result:") < out.index("  archi-kg:") < out.index("  collector:")
    mocks["publish_post"].assert_not_called()


def test_main_marks_a_missing_integrity_detail_instead_of_crashing(monkeypatch, tmp_path, capsys):
    units = [_unit("u1", "invalid", {"repo": "brain"})]

    _gated_run(monkeypatch, tmp_path, units)

    assert "  brain: integrity_status=invalid detail=<missing>" in capsys.readouterr().out


def test_main_proceeds_when_only_a_block_record_exists(monkeypatch, tmp_path):
    registry_dir = tmp_path / "registry"
    monkeypatch.setattr(daily_publish.registry_writer, "OUTPUT_DIR", str(registry_dir))
    daily_publish.registry_writer.write_record(_block_record())

    # write_record is mocked for the final pass-record write only: a real
    # write would hit a gate_status disagreement against the existing
    # block record (writer.py outcome 4). That later-stage behavior is not
    # what this test covers — only that a block record doesn't stop the
    # publish path from being reached.
    write_record = mock.Mock(return_value="path")
    monkeypatch.setattr(daily_publish.registry_writer, "write_record", write_record)

    mocks, _ = _run_main(monkeypatch, tmp_path)

    mocks["call_model"].assert_called_once()
    mocks["publish_post"].assert_called_once_with("post text")
    written = write_record.call_args.args[0]
    assert written.gate_status == "pass"
    assert written.content_id == _CONTENT_ID


def test_main_raises_and_does_not_publish_when_record_is_unparseable(monkeypatch, tmp_path):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    record_file = registry_dir / f"{_CONTENT_ID}.json"
    record_file.write_text("{not valid json", encoding="utf-8")
    original_bytes = record_file.read_bytes()
    mocks = _setup_main(monkeypatch, tmp_path)

    with pytest.raises(daily_publish.registry_writer.PublicationRegistryConflictError):
        daily_publish.main()

    mocks["publish_post"].assert_not_called()
    mocks["call_model"].assert_not_called()
    assert record_file.read_bytes() == original_bytes


def test_main_publishes_and_writes_pass_record_when_no_record_exists(monkeypatch, tmp_path):
    mocks, registry_dir = _run_main(monkeypatch, tmp_path)

    mocks["call_model"].assert_called_once()
    mocks["publish_post"].assert_called_once_with("post text")
    written = json.loads((registry_dir / f"{_CONTENT_ID}.json").read_text(encoding="utf-8"))
    assert written["gate_status"] == "pass"
    assert written["url"] == _POST_URL
    assert written["content_id"] == _CONTENT_ID


# --- main(): real call order around the model-response verification ---------
#
# validate_structured_response() is NOT mocked here (unlike _setup_main's
# default). These tests pin the actual sequence in main(): the model is
# called, its response is verified against the clusters offered this run,
# and only then may publish_post() and registry_writer.write_record() run.

_SHAPED_BRIEF = {
    "mode": "fact",
    "date": "2026-09-24",
    "total_diffstat": 10,
    "files_touched": ["a.py"],
    "commit_messages": ["fix: alpha"],
    "per_repo": [
        {"name": "r", "commit_count": 1, "diffstat": 10, "files_touched": ["a.py"],
         "commit_messages": ["fix: alpha"]},
    ],
}

_GOOD_CITATION = {
    "post": "I pushed a commit to r.",
    "fact_or_product": "fix: alpha",
    "selected_cluster": "r",
    "supporting_facts": ["r:fact_01"],
}


def _setup_real_validation(monkeypatch, tmp_path, model_response):
    real_validate = daily_publish.daily_linkedin_author.validate_structured_response
    mocks = _setup_main(monkeypatch, tmp_path)
    calls = []

    def spy_validate(response, mode, daily_brief=None):
        calls.append("validate")
        return real_validate(response, mode, daily_brief)

    def spy_publish(text):
        calls.append("publish_post")
        return _POST_URL

    def spy_write(record):
        calls.append("write_record")
        return "path"

    monkeypatch.setattr(
        daily_publish, "build_daily_brief_from_authoring_contexts", lambda contexts, date: _SHAPED_BRIEF
    )
    monkeypatch.setattr(daily_publish.daily_linkedin_author, "call_model", mock.Mock(return_value=model_response))
    monkeypatch.setattr(daily_publish.daily_linkedin_author, "validate_structured_response", spy_validate)
    monkeypatch.setattr(daily_publish.linkedin_client, "publish_post", spy_publish)
    monkeypatch.setattr(daily_publish.registry_writer, "write_record", spy_write)
    return mocks, calls


@pytest.mark.parametrize(
    "bad_response",
    [
        pytest.param({**_GOOD_CITATION, "selected_cluster": "not-offered"}, id="cluster-not-offered"),
        pytest.param({**_GOOD_CITATION, "supporting_facts": ["other:fact_01"]}, id="fact-id-from-unoffered-cluster"),
        pytest.param({**_GOOD_CITATION, "supporting_facts": ["r:fact_99"]}, id="fact-id-not-in-cluster"),
        pytest.param({k: v for k, v in _GOOD_CITATION.items() if k != "supporting_facts"}, id="missing-key"),
    ],
)
def test_failed_fact_verification_raises_before_publish_and_before_any_registry_write(
    monkeypatch, tmp_path, bad_response
):
    mocks, calls = _setup_real_validation(monkeypatch, tmp_path, bad_response)

    with pytest.raises(daily_publish.daily_linkedin_author.AuthorLLMError):
        daily_publish.main()

    assert calls == ["validate"], f"only validation may have run, got {calls}"
    daily_publish.daily_linkedin_author.call_model.assert_called_once()
    registry_dir = tmp_path / "registry"
    assert not registry_dir.exists() or list(registry_dir.iterdir()) == []


def test_write_record_raising_if_called_is_never_reached_on_a_failed_verification(monkeypatch, tmp_path):
    # Same scenario with write_record wired to raise if it is ever invoked:
    # the only exception that may escape is the verification failure.
    mocks, _ = _setup_real_validation(
        monkeypatch, tmp_path, {**_GOOD_CITATION, "supporting_facts": ["other:fact_01"]}
    )
    boom = mock.Mock(side_effect=RuntimeError("write_record must not be called"))
    monkeypatch.setattr(daily_publish.registry_writer, "write_record", boom)

    with pytest.raises(daily_publish.daily_linkedin_author.AuthorLLMError, match="other:fact_01"):
        daily_publish.main()

    boom.assert_not_called()


def test_well_formed_citation_validates_then_publishes_then_writes_in_that_order(monkeypatch, tmp_path):
    _, calls = _setup_real_validation(monkeypatch, tmp_path, dict(_GOOD_CITATION))

    daily_publish.main()

    assert calls == ["validate", "publish_post", "write_record"]
