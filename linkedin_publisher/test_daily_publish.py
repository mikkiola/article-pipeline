"""Tests for linkedin_publisher/daily_publish.py's extracted, testable
functions — resolve_daily_brief_path(), build_content_id(),
pick_representative_claim_id(), build_block_record(), build_pass_record(),
classify_gate_block() — and for the run-outcome contract (one Outcome and
one exit code per run, via main()).

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

    # Identity continuity (ADR-0059 Decision point 6): redirect to
    # tmp_path so no test ever reads or writes this repo's own real
    # author/state/ files, matching the Registry's own tmp_path
    # redirection above.
    state_dir = tmp_path / "identity_state_dir"
    monkeypatch.setattr(daily_publish.identity_state, "STATE_DIR", str(state_dir))
    monkeypatch.setattr(daily_publish.identity_state, "IDENTITY_STATE_FILE", str(state_dir / "identity_state.json"))
    monkeypatch.setattr(daily_publish.identity_state, "RECENT_POSTS_FILE", str(state_dir / "recent_posts.json"))

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
    monkeypatch.setattr(
        daily_publish.daily_linkedin_author,
        "build_prompt",
        lambda brief, identity_state=None, recent_posts=None: "prompt",
    )
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
        daily_publish.run()

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


# --- main(): identity continuity (ADR-0059 Decision point 6) ---------------


def test_main_passes_loaded_identity_state_and_recent_posts_into_build_prompt(monkeypatch, tmp_path):
    mocks = _setup_main(monkeypatch, tmp_path)
    seeded_state = {**daily_publish.identity_state.DEFAULT_IDENTITY_STATE, "trajectory": "seeded state"}
    daily_publish.identity_state.write_identity_state(seeded_state)
    daily_publish.identity_state.append_recent_post("an earlier real post")

    build_prompt_spy = mock.Mock(return_value="prompt")
    monkeypatch.setattr(daily_publish.daily_linkedin_author, "build_prompt", build_prompt_spy)

    daily_publish.main()

    build_prompt_spy.assert_called_once()
    call_kwargs = build_prompt_spy.call_args.kwargs
    assert call_kwargs["identity_state"] == seeded_state
    assert call_kwargs["recent_posts"] == ["an earlier real post"]


def test_main_appends_published_post_text_to_recent_posts_after_publish(monkeypatch, tmp_path):
    _run_main(monkeypatch, tmp_path)

    assert daily_publish.identity_state.load_recent_posts() == ["post text"]


def test_main_does_not_append_recent_post_when_gate_blocks(monkeypatch, tmp_path):
    units = [_unit("u1", "invalid", {"repo": "r", "integrity_check_detail": "d"})]

    _gated_run(monkeypatch, tmp_path, units)

    assert daily_publish.identity_state.load_recent_posts() == []


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
    "automation_only_day": False,
    "post": "I pushed a commit to r.",
    "selected_cluster": "r",
    "supporting_facts": ["r:fact_01"],
    "reasoning": {
        "fact": "One commit landed in r.",
        "tension": "A fix landed with no accompanying test change.",
        "design_insight": "The author treats a narrow fix as complete on its own.",
        "personal_position": "I want fixes to stay small enough to land alone.",
        "relevant_problem": "Small fixes can hide in larger, harder-to-review batches.",
    },
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
        daily_publish.run()

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
        daily_publish.run()

    boom.assert_not_called()


def test_well_formed_citation_validates_then_publishes_then_writes_in_that_order(monkeypatch, tmp_path):
    _, calls = _setup_real_validation(monkeypatch, tmp_path, dict(_GOOD_CITATION))

    daily_publish.main()

    assert calls == ["validate", "publish_post", "write_record"]


# --- main(): automation-only-day guard (ADR-0059 Decision point 7) --------
# Prompt-level guard: the model was still called and validated, but honestly
# reported nothing to publish today. B-069's separate pre-call skip (never
# calling the model at all) is not exercised here.

_GOOD_AUTOMATION_ONLY_RESPONSE = {
    "automation_only_day": True,
    "post": "",
    "selected_cluster": "r",
    "supporting_facts": [],
    "reasoning": {
        "fact": "The selected cluster's only commit was an automated, scheduled "
                "process's own output, with no manual engineering work alongside it.",
        "tension": "", "design_insight": "", "personal_position": "", "relevant_problem": "",
    },
}


def test_main_skips_publish_and_registry_write_on_automation_only_day_response(monkeypatch, tmp_path, capsys):
    _, calls = _setup_real_validation(monkeypatch, tmp_path, dict(_GOOD_AUTOMATION_ONLY_RESPONSE))

    daily_publish.main()

    assert calls == ["validate"], f"publish_post/write_record must not run, got {calls}"
    assert "Automation-only day detected" in capsys.readouterr().out
    registry_dir = tmp_path / "registry"
    assert not registry_dir.exists() or list(registry_dir.iterdir()) == []


def test_main_does_not_append_recent_post_on_automation_only_day(monkeypatch, tmp_path):
    _setup_real_validation(monkeypatch, tmp_path, dict(_GOOD_AUTOMATION_ONLY_RESPONSE))

    daily_publish.main()

    assert daily_publish.identity_state.load_recent_posts() == []


# --- main(): run-outcome contract (SPEC.md run-outcome requirement) ---------
#
# One Outcome and one exit code per run. gate_status stays pass/block; the
# outcome is additional signal only.
#
# FACT about reachability: through the real Collector adapter + pre_filter, a
# valid unit is always `include` (valid + corroboration_status
# "not_applicable"), so a gate block caused ONLY by non-integrity exclusion of
# valid units cannot be produced from real Collector data today. The
# SKIPPED_NO_ELIGIBLE_CONTENT branch is therefore tested by injecting
# gate_result / pre_filter_results (as _gated_run does), not by fabricating a
# data shape the real pipeline cannot emit.

_REAL_ADAPT = daily_publish.collector_adapter.adapt_daily_brief
_REAL_RUN_PRE_FILTER = daily_publish.pre_filter.run_pre_filter
_REAL_CHECK_GATE = daily_publish.pre_filter.check_gate_condition


def _exclude_all(units, reason="excluded"):
    return [
        {"claim_id": u.unit_id, "pre_filter_classification": "exclude", "reason": reason}
        for u in units
    ]


def _inject_gated(monkeypatch, units, reason="excluded"):
    monkeypatch.setattr(daily_publish.collector_adapter, "adapt_daily_brief", lambda brief: units)
    monkeypatch.setattr(daily_publish.pre_filter, "run_pre_filter", lambda us: _exclude_all(us, reason))
    monkeypatch.setattr(
        daily_publish.pre_filter,
        "check_gate_condition",
        lambda results: {"status": "gated", "gates": {"zero_included_units": True}},
    )


def _valid_unit(unit_id="u1", repo="r"):
    return SimpleNamespace(
        unit_id=unit_id,
        integrity_status="valid",
        integrity_check_method="ancestry_reconciliation",
        corroboration_status="not_applicable",
        metadata={
            "repo": repo, "commit_count": 1, "diffstat": 10, "branch": "main",
            "integrity_check_detail": "identical",
        },
    )


def _invalid_unit(unit_id="u2", repo="archi-kg", detail="daily_brief schema_version=3, expected 2"):
    return SimpleNamespace(
        unit_id=unit_id,
        integrity_status="invalid",
        integrity_check_method="ancestry_reconciliation",
        corroboration_status="not_applicable",
        metadata={
            "repo": repo, "commit_count": 1, "diffstat": 10, "branch": "main",
            "integrity_check_detail": detail,
        },
    )


def _registry_is_empty(tmp_path):
    registry_dir = tmp_path / "registry"
    return not registry_dir.exists() or list(registry_dir.iterdir()) == []


def test_published_outcome_exit_0_and_pass_record(monkeypatch, tmp_path, capsys):
    mocks = _setup_main(monkeypatch, tmp_path)

    code = daily_publish.main()

    assert code == 0
    assert "OUTCOME=PUBLISHED exit_code=0" in capsys.readouterr().out
    mocks["publish_post"].assert_called_once_with("post text")
    written = json.loads((tmp_path / "registry" / f"{_CONTENT_ID}.json").read_text(encoding="utf-8"))
    assert written["gate_status"] == "pass"


def test_exit_code_map_matches_the_accepted_contract():
    zero = {
        "PUBLISHED", "SKIPPED_NO_ELIGIBLE_CONTENT", "SKIPPED_SAFETY_PAUSE",
        "SKIPPED_ALREADY_PUBLISHED", "SKIPPED_AUTOMATION_ONLY",
    }
    one = {"FAILED_INTEGRITY", "FAILED"}
    assert {o.value for o in daily_publish.Outcome} == zero | one
    for outcome, code in daily_publish.EXIT_CODES.items():
        assert code == (0 if outcome.value in zero else 1)


# SKIPPED_NO_ELIGIBLE_CONTENT

def test_gate_block_without_integrity_violation_is_skipped_no_eligible_and_writes_block_record(
    monkeypatch, tmp_path, capsys
):
    mocks = _setup_main(monkeypatch, tmp_path)
    _inject_gated(monkeypatch, [_valid_unit("u1", "r")], reason="Disputed evidence")

    code = daily_publish.main()

    assert code == 0
    assert "OUTCOME=SKIPPED_NO_ELIGIBLE_CONTENT exit_code=0" in capsys.readouterr().out
    written = json.loads((tmp_path / "registry" / f"{_CONTENT_ID}.json").read_text(encoding="utf-8"))
    assert written["gate_status"] == "block"
    mocks["call_model"].assert_not_called()
    mocks["publish_post"].assert_not_called()


def test_classify_gate_block_valid_units_only_is_skipped_no_eligible():
    units = [_valid_unit("u1"), _valid_unit("u3", "other")]
    results = _exclude_all(units, reason="Pending")

    result = daily_publish.classify_gate_block(units, results)

    assert result.outcome is daily_publish.Outcome.SKIPPED_NO_ELIGIBLE_CONTENT
    assert result.diagnostics["excluded_units"] == 2
    assert result.diagnostics["exclusion_reasons"] == ["Pending"]


# SKIPPED_SAFETY_PAUSE

def test_safety_pause_open_is_skipped_before_any_io(monkeypatch, tmp_path, capsys):
    mocks = _setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(daily_publish, "check_safety_pause_state", lambda: daily_publish.SafetyPauseState.OPEN)
    preflight = mock.Mock(side_effect=RuntimeError("preflight must not run"))
    adapt = mock.Mock(side_effect=RuntimeError("adapter must not run"))
    monkeypatch.setattr(daily_publish.linkedin_client, "check_token_preflight", preflight)
    monkeypatch.setattr(daily_publish.collector_adapter, "adapt_daily_brief", adapt)

    code = daily_publish.main()

    assert code == 0
    assert "OUTCOME=SKIPPED_SAFETY_PAUSE exit_code=0" in capsys.readouterr().out
    preflight.assert_not_called()
    adapt.assert_not_called()
    mocks["publish_post"].assert_not_called()
    assert _registry_is_empty(tmp_path)


# SKIPPED_ALREADY_PUBLISHED

def test_already_published_outcome_exit_0(monkeypatch, tmp_path, capsys):
    registry_dir = tmp_path / "registry"
    monkeypatch.setattr(daily_publish.registry_writer, "OUTPUT_DIR", str(registry_dir))
    daily_publish.registry_writer.write_record(_pass_record())

    mocks, _ = _run_main(monkeypatch, tmp_path)
    out = capsys.readouterr().out

    assert "OUTCOME=SKIPPED_ALREADY_PUBLISHED exit_code=0" in out
    assert _POST_URL in out
    mocks["publish_post"].assert_not_called()


def test_already_published_wins_over_invalid_input(monkeypatch, tmp_path, capsys):
    registry_dir = tmp_path / "registry"
    monkeypatch.setattr(daily_publish.registry_writer, "OUTPUT_DIR", str(registry_dir))
    daily_publish.registry_writer.write_record(_pass_record())
    record_file = registry_dir / f"{_CONTENT_ID}.json"
    original_bytes = record_file.read_bytes()
    mocks = _setup_main(monkeypatch, tmp_path)
    _inject_gated(monkeypatch, [_invalid_unit("u1", "r")])

    code = daily_publish.main()

    assert code == 0
    assert "OUTCOME=SKIPPED_ALREADY_PUBLISHED exit_code=0" in capsys.readouterr().out
    mocks["call_model"].assert_not_called()
    mocks["publish_post"].assert_not_called()
    assert record_file.read_bytes() == original_bytes


# SKIPPED_AUTOMATION_ONLY

def test_automation_only_day_outcome_exit_0_and_no_registry_record(monkeypatch, tmp_path, capsys):
    _setup_real_validation(monkeypatch, tmp_path, dict(_GOOD_AUTOMATION_ONLY_RESPONSE))

    code = daily_publish.main()
    out = capsys.readouterr().out

    assert code == 0
    assert "OUTCOME=SKIPPED_AUTOMATION_ONLY exit_code=0" in out
    assert "selected_cluster: r" in out
    assert _registry_is_empty(tmp_path)


# FAILED_INTEGRITY

def test_schema_mismatch_is_failed_integrity_with_specific_diagnostic(monkeypatch, tmp_path, capsys):
    mocks = _setup_main(monkeypatch, tmp_path)
    # Real adapter, real pre_filter, real gate: a schema-incompatible brief.
    monkeypatch.setattr(daily_publish.collector_adapter, "adapt_daily_brief", _REAL_ADAPT)
    monkeypatch.setattr(daily_publish.pre_filter, "run_pre_filter", _REAL_RUN_PRE_FILTER)
    monkeypatch.setattr(daily_publish.pre_filter, "check_gate_condition", _REAL_CHECK_GATE)
    expected = daily_publish.collector_adapter.DAILY_BRIEF_SCHEMA_VERSION
    brief = {
        "date": "2026-09-24",
        "schema_version": expected - 1,
        "mode": "fact",
        "commit_messages": [],
        "per_repo": [
            {"name": "archi-kg", "branch": "main", "head_sha": "a" * 40, "commit_count": 1,
             "diffstat": 10, "files_touched": ["a.py"]},
            {"name": "brain", "branch": "main", "head_sha": "b" * 40, "commit_count": 2,
             "diffstat": 20, "files_touched": ["b.py"]},
        ],
    }
    brief_path = tmp_path / "daily_brief_2026-09-24.json"
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    outcome_file = tmp_path / "outcome.json"
    monkeypatch.setenv(daily_publish.OUTCOME_PATH_ENV, str(outcome_file))

    code = daily_publish.main()
    out = capsys.readouterr().out

    assert code == 1
    assert "gate_result: {'status': 'gated', 'gates': {'zero_included_units': True}}" in out
    assert "OUTCOME=FAILED_INTEGRITY exit_code=1" in out
    specific = f"schema_version={expected - 1}, expected {expected}"
    payload = json.loads(outcome_file.read_text(encoding="utf-8"))
    assert payload["outcome"] == "FAILED_INTEGRITY"
    assert payload["exit_code"] == 1
    violations = payload["diagnostics"]["integrity_violations"]
    assert {v["repo"] for v in violations} == {"archi-kg", "brain"}
    assert all(specific in v["detail"] for v in violations)
    assert specific in out
    mocks["call_model"].assert_not_called()
    mocks["publish_post"].assert_not_called()


def test_mixed_invalid_and_excluded_is_failed_integrity(monkeypatch, tmp_path, capsys):
    # Injected: not producible from real Collector data (see the FACT above).
    mocks = _setup_main(monkeypatch, tmp_path)
    _inject_gated(monkeypatch, [_invalid_unit("u2"), _valid_unit("u1")])

    code = daily_publish.main()

    assert code == 1
    assert "OUTCOME=FAILED_INTEGRITY exit_code=1" in capsys.readouterr().out
    mocks["call_model"].assert_not_called()
    mocks["publish_post"].assert_not_called()


def test_classify_gate_block_any_invalid_excluded_unit_is_failed_integrity():
    units = [_valid_unit("u1"), _invalid_unit("u2", "brain", "no head_sha recorded")]

    result = daily_publish.classify_gate_block(units, _exclude_all(units))

    assert result.outcome is daily_publish.Outcome.FAILED_INTEGRITY
    assert result.diagnostics["integrity_violations"] == [
        {"repo": "brain", "detail": "no head_sha recorded"}
    ]


def test_failed_integrity_does_not_write_block_registry_record(monkeypatch, tmp_path):
    mocks = _setup_main(monkeypatch, tmp_path)
    _inject_gated(monkeypatch, [_invalid_unit("u1", "r")])

    code = daily_publish.main()

    assert code == 1
    assert _registry_is_empty(tmp_path)
    mocks["call_model"].assert_not_called()
    mocks["publish_post"].assert_not_called()
    assert daily_publish.identity_state.load_recent_posts() == []


def test_failed_integrity_outcome_states_retention_limit(monkeypatch, tmp_path, capsys):
    _setup_main(monkeypatch, tmp_path)
    _inject_gated(monkeypatch, [_invalid_unit("u1", "r")])
    outcome_file = tmp_path / "outcome.json"
    monkeypatch.setenv(daily_publish.OUTCOME_PATH_ENV, str(outcome_file))

    daily_publish.main()

    assert daily_publish.RETENTION_NOTE in capsys.readouterr().out
    payload = json.loads(outcome_file.read_text(encoding="utf-8"))
    assert payload["retention_note"] == daily_publish.RETENTION_NOTE
    assert "not a durable archive" in payload["retention_note"]


def test_partial_invalid_with_one_included_still_publishes(monkeypatch, tmp_path, capsys):
    # Per-unit exclusion policy is unchanged: an invalid unit is excluded and
    # the valid one still goes through. Real pre_filter and real gate.
    mocks = _setup_main(monkeypatch, tmp_path)
    units = [_invalid_unit("u2"), _valid_unit("u1")]
    monkeypatch.setattr(daily_publish.collector_adapter, "adapt_daily_brief", lambda brief: units)
    monkeypatch.setattr(daily_publish.pre_filter, "run_pre_filter", _REAL_RUN_PRE_FILTER)
    monkeypatch.setattr(daily_publish.pre_filter, "check_gate_condition", _REAL_CHECK_GATE)

    code = daily_publish.main()

    assert code == 0
    assert "OUTCOME=PUBLISHED exit_code=0" in capsys.readouterr().out
    mocks["publish_post"].assert_called_once_with("post text")


# FAILED

def _boom_preflight(monkeypatch, mocks):
    monkeypatch.setattr(
        daily_publish.linkedin_client,
        "check_token_preflight",
        mock.Mock(side_effect=daily_publish.linkedin_client.LinkedInPublisherError("token expired")),
    )


def _missing_brief(monkeypatch, mocks):
    monkeypatch.setattr(
        daily_publish,
        "parse_args",
        lambda: argparse.Namespace(daily_brief_path="/nonexistent/daily_brief.json"),
    )


def _unparseable_model_response(monkeypatch, mocks):
    monkeypatch.setattr(
        daily_publish.daily_linkedin_author,
        "call_model",
        mock.Mock(side_effect=daily_publish.daily_linkedin_author.AuthorLLMError("not parseable")),
    )


def _publish_error(monkeypatch, mocks):
    monkeypatch.setattr(
        daily_publish.linkedin_client,
        "publish_post",
        mock.Mock(side_effect=daily_publish.linkedin_client.LinkedInPublisherError("LinkedIn 403")),
    )


@pytest.mark.parametrize(
    "break_it",
    [
        pytest.param(_boom_preflight, id="token-preflight"),
        pytest.param(_missing_brief, id="missing-brief-file"),
        pytest.param(_unparseable_model_response, id="model-response-unparseable"),
        pytest.param(_publish_error, id="publish-call-fails"),
    ],
)
def test_unexpected_error_is_failed_exit_1(monkeypatch, tmp_path, capsys, break_it):
    mocks = _setup_main(monkeypatch, tmp_path)
    break_it(monkeypatch, mocks)

    code = daily_publish.main()

    assert code == 1
    assert "OUTCOME=FAILED exit_code=1" in capsys.readouterr().out
    assert _registry_is_empty(tmp_path)


def test_registry_write_failure_after_confirmed_publish_fails_job_and_keeps_url(
    monkeypatch, tmp_path, capsys
):
    mocks = _setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(
        daily_publish.registry_writer,
        "write_record",
        mock.Mock(side_effect=daily_publish.registry_writer.PublicationRegistryConflictError("disk")),
    )
    outcome_file = tmp_path / "outcome.json"
    monkeypatch.setenv(daily_publish.OUTCOME_PATH_ENV, str(outcome_file))

    code = daily_publish.main()
    out = capsys.readouterr().out

    assert code == 1
    assert "OUTCOME=FAILED exit_code=1" in out
    assert _POST_URL in out
    mocks["publish_post"].assert_called_once_with("post text")
    payload = json.loads(outcome_file.read_text(encoding="utf-8"))
    diagnostics = payload["diagnostics"]
    assert diagnostics["publication"] == "confirmed"
    assert diagnostics["url"] == _POST_URL
    assert diagnostics["persistence"] == "failed"
    assert [f["stage"] for f in diagnostics["persistence_failures"]] == ["registry_record"]
    # The published text is still remembered: persistence steps are independent.
    assert daily_publish.identity_state.load_recent_posts() == ["post text"]


def test_recent_post_append_failure_after_publish_is_reported_not_swallowed(
    monkeypatch, tmp_path, capsys
):
    mocks = _setup_main(monkeypatch, tmp_path)
    monkeypatch.setattr(
        daily_publish.identity_state, "append_recent_post", mock.Mock(side_effect=OSError("read-only fs"))
    )

    code = daily_publish.main()
    out = capsys.readouterr().out

    assert code == 1
    assert _POST_URL in out
    assert "recent_posts" in out
    mocks["publish_post"].assert_called_once_with("post text")
    # The Registry record (the duplicate-publish guard) was still written.
    written = json.loads((tmp_path / "registry" / f"{_CONTENT_ID}.json").read_text(encoding="utf-8"))
    assert written["gate_status"] == "pass"


def test_existing_block_record_then_publish_reports_persistence_conflict_with_url(
    monkeypatch, tmp_path, capsys
):
    # Real writer: a block record already at this content_id disagrees with
    # the pass record (writer outcome 4). Documents the persistence conflict;
    # it must fail the job with the URL preserved and publish exactly once.
    registry_dir = tmp_path / "registry"
    monkeypatch.setattr(daily_publish.registry_writer, "OUTPUT_DIR", str(registry_dir))
    daily_publish.registry_writer.write_record(_block_record())
    record_file = registry_dir / f"{_CONTENT_ID}.json"
    original_bytes = record_file.read_bytes()

    mocks = _run_main_returning_code(monkeypatch, tmp_path)
    out = capsys.readouterr().out

    assert mocks["code"] == 1
    assert "OUTCOME=FAILED exit_code=1" in out
    assert _POST_URL in out
    mocks["publish_post"].assert_called_once_with("post text")
    assert record_file.read_bytes() == original_bytes


def _run_main_returning_code(monkeypatch, tmp_path):
    mocks = _setup_main(monkeypatch, tmp_path)
    mocks["code"] = daily_publish.main()
    return mocks


# Outcome file

def test_outcome_file_is_written_when_env_set_and_not_in_registry_dir(monkeypatch, tmp_path):
    _setup_main(monkeypatch, tmp_path)
    outcome_file = tmp_path / "out" / "outcome.json"
    outcome_file.parent.mkdir()
    monkeypatch.setenv(daily_publish.OUTCOME_PATH_ENV, str(outcome_file))

    daily_publish.main()

    payload = json.loads(outcome_file.read_text(encoding="utf-8"))
    assert payload["outcome"] == "PUBLISHED"
    assert "retention_note" not in payload
    assert [p.name for p in (tmp_path / "registry").iterdir()] == [f"{_CONTENT_ID}.json"]


def test_no_outcome_file_when_env_unset(monkeypatch, tmp_path):
    _setup_main(monkeypatch, tmp_path)
    monkeypatch.delenv(daily_publish.OUTCOME_PATH_ENV, raising=False)

    daily_publish.main()

    assert not list(tmp_path.glob("**/outcome*.json"))


def test_outcome_file_write_failure_does_not_change_exit_code(monkeypatch, tmp_path, capsys):
    _setup_main(monkeypatch, tmp_path)
    monkeypatch.setenv(daily_publish.OUTCOME_PATH_ENV, str(tmp_path / "no" / "such" / "dir" / "o.json"))

    code = daily_publish.main()

    assert code == 0
    assert "WARNING: could not write outcome file" in capsys.readouterr().out


# main()-level coverage of failures that the run()-level tests only cover
# through the exception.

def test_failed_fact_verification_through_main_is_failed_exit_1_before_publish(
    monkeypatch, tmp_path, capsys
):
    mocks, calls = _setup_real_validation(
        monkeypatch, tmp_path, {**_GOOD_CITATION, "supporting_facts": ["other:fact_01"]}
    )

    code = daily_publish.main()

    assert code == 1
    assert "OUTCOME=FAILED exit_code=1" in capsys.readouterr().out
    assert calls == ["validate"]
    assert _registry_is_empty(tmp_path)


def test_unparseable_registry_record_through_main_is_failed_exit_1_and_does_not_publish(
    monkeypatch, tmp_path, capsys
):
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    (registry_dir / f"{_CONTENT_ID}.json").write_text("{not valid json", encoding="utf-8")
    mocks = _setup_main(monkeypatch, tmp_path)

    code = daily_publish.main()

    assert code == 1
    assert "OUTCOME=FAILED exit_code=1" in capsys.readouterr().out
    mocks["publish_post"].assert_not_called()
    mocks["call_model"].assert_not_called()
