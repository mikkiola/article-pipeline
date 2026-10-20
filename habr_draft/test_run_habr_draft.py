"""End-to-end tests of stage 2 with the model caller and GitHub injected.
No network, no paid call, no real secret."""

import json

import pytest

from habr_draft import run_habr_draft
from habr_draft.fragments import FetchResult
from habr_draft.testsupport import (
    GOOD_BODY, ScriptedCaller, fetch_ok, good_plan, make_config, selection_ok, write_selection,
)

DATE = "2026-10-15"
SENTINEL = "SENTINEL-RAW-MODEL-TEXT-9f3a"


def go(tmp_path, *, selection=None, config=None, caller=None, mode="production", fetch_fn=fetch_ok,
       visibility=lambda r: True, env=None):
    out = tmp_path / "out"
    record = run_habr_draft.run(
        selection_path=write_selection(tmp_path, selection or selection_ok()),
        date=DATE, mode=mode, output_dir=out, config=config or make_config(),
        env=env or {"GITHUB_APP_TOKEN": "narrow", "ARTICLE_PIPELINE_SHA": "1" * 40,
                    "COLLECTOR_SHA": "2" * 40},
        caller=caller, fetch_fn=fetch_fn, visibility=visibility,
    )
    return record, out


def read_record(out):
    (path,) = out.glob("run_*.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_production_pass_writes_attempt_and_record_with_provenance(tmp_path):
    caller = ScriptedCaller(good_plan())
    record, out = go(tmp_path, caller=caller)
    assert record["terminal_outcome"] == "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW"
    saved = read_record(out)
    assert saved["terminal_outcome"] == saved["observable_outcome"]
    prov = saved["provenance"]
    assert prov["article_pipeline_sha"] == "1" * 40 and prov["collector_sha"] == "2" * 40
    assert prov["daily_brief_sha256"] == "d" * 64
    assert len(prov["acceptance_config_sha256"]) == 64 and len(prov["rubric_sha256"]) == 64
    assert saved["fragments"]["used"][0]["sha"] == "a" * 40
    assert "not publication approval" in saved["report"]
    assert (out / "attempt_1.md").exists()
    assert {c["name"] for c in saved["rounds"][0]["checks"]} == {
        "l1_fact_verification", "habr_rules", "project_requirements", "q_infostyle"}
    # model, key variable and per-purpose limits come from config
    assert {c["model"] for c in caller.calls} == {"claude-sonnet-5-5"}
    assert {c["api_key_env"] for c in caller.calls} == {"ANTHROPIC_API_KEY_HABR_DRAFT"}


def test_blocked_after_two_corrections_keeps_all_attempts(tmp_path):
    plan = good_plan()
    plan["q"] = [{"score": 10, "findings": [{"criterion": "ai_markers", "severity": "major"}]}]
    caller = ScriptedCaller(plan)
    record, out = go(tmp_path, caller=caller)
    assert record["terminal_outcome"] == "BLOCKED"
    assert sorted(p.name for p in out.glob("attempt_*.md")) == ["attempt_1.md", "attempt_2.md", "attempt_3.md"]
    assert [c["purpose"] for c in caller.calls].count("generation") == 1
    assert [c["purpose"] for c in caller.calls].count("revision") == 2


def test_missing_threshold_stops_before_any_paid_call_as_missing_configuration(tmp_path):
    caller = ScriptedCaller(good_plan())
    record, out = go(tmp_path, config=make_config(q_threshold=None), caller=caller)
    assert caller.calls == []
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["failure_kind"] == "missing_configuration"
    assert record["q_threshold_unset"] is True
    assert "q_threshold" in record["reason"]


def test_paid_calls_disabled_by_default_blocks_every_call(tmp_path):
    caller = ScriptedCaller(good_plan())
    record, _ = go(tmp_path, config=make_config(paid_calls_enabled=False), caller=caller)
    assert caller.calls == [] and record["failure_kind"] == "missing_configuration"
    assert "paid_calls_enabled" in record["reason"]


def test_no_eligible_topic_is_not_a_system_failure_and_calls_no_model(tmp_path):
    caller = ScriptedCaller(good_plan())
    record, out = go(tmp_path, caller=caller, fetch_fn=lambda u: FetchResult())
    assert caller.calls == []
    assert record["terminal_outcome"] is None
    assert record["observable_outcome"] == "NO_ELIGIBLE_TOPIC"
    assert record["reason"] == "no_eligible_topic" and record["failure_kind"] is None
    assert list(out.glob("attempt_*.md")) == []


def test_technical_fetch_error_is_system_failure_not_no_eligible_topic(tmp_path):
    record, _ = go(tmp_path, caller=ScriptedCaller(good_plan()),
                   fetch_fn=lambda u: FetchResult(errors=[{"kind": "http", "status": 503}]))
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["reason"] == "fragment_fetch_error" and record["failure_kind"] == "execution_error"


def test_failed_preflight_records_system_failure_without_any_call(tmp_path):
    selection = {"status": "failed", "reason": "daily_brief_missing", "detail": "no file",
                 "date": DATE, "daily_brief_sha256": None}
    caller = ScriptedCaller(good_plan())
    record, out = go(tmp_path, selection=selection, caller=caller)
    assert caller.calls == []
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["failure_kind"] == "input_validation"
    assert "daily_brief_missing" in record["reason"]
    assert read_record(out)["run_id"] == record["run_id"]


def test_budget_refusal_happens_before_the_call_and_is_best_effort(tmp_path):
    caller = ScriptedCaller(good_plan())
    from habr_draft.config import Budget
    cfg = make_config(budget=Budget(max_run_spend_usd=0.000001, max_fragment_chars_per_attempt=10000,
                                    max_tokens_generation=1000, max_tokens_judge=500,
                                    price_in_per_mtok=2.0, price_out_per_mtok=10.0))
    record, _ = go(tmp_path, config=cfg, caller=caller)
    assert caller.calls == []
    assert record["terminal_outcome"] == "SYSTEM_FAILURE" and record["failure_kind"] == "budget_limit"
    assert record["budget"]["guard"] == "best_effort"


def test_output_secret_gate_discards_text_everywhere(tmp_path, capsys):
    secret = "gh" + "p_" + "D" * 36
    plan = good_plan()
    leaking = {"title": "T", "body_markdown": GOOD_BODY + f"\nключ {secret}\n",
               "selected_cluster": "article-pipeline", "supporting_facts": ["article-pipeline:fact_01"]}
    plan["generation"] = [leaking]
    caller = ScriptedCaller(plan)
    record, out = go(tmp_path, caller=caller)
    everything = "".join(p.read_text(encoding="utf-8") for p in out.iterdir())
    printed = capsys.readouterr()
    assert secret not in everything and secret not in printed.out and secret not in printed.err
    first = record["rounds"][0]
    assert first["saved"] is False and first["attempt_file"] is None and first["checks"] == []
    assert first["secret_hits"] == [{"pattern_id": "github-token", "count": 1}]
    # the leaked text was not sent to a judge nor into the revision prompt
    assert all(secret not in c["prompt"] for c in caller.calls)
    assert [c["purpose"] for c in caller.calls][:2] == ["generation", "revision"]
    assert "(the previous draft was discarded" in caller.calls[1]["prompt"]
    assert record["terminal_outcome"] == "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW"


def test_prompts_mark_commit_text_and_code_as_untrusted_data(tmp_path):
    caller = ScriptedCaller(good_plan())
    go(tmp_path, caller=caller)
    for call in caller.calls:
        assert "untrusted" in call["system"].lower()
        assert "not instructions" in call["system"]


# ---- raw-exception-text suppression across every paid call site ---------------

PURPOSES = ["generation", "revision", "l1", "q", "reference"]


def _scenario(purpose):
    """A plan + mode in which `purpose` is reached, and raises with the raw
    response text in its message (as call_model's JSON error does)."""
    import daily_linkedin_author

    plan = good_plan()
    mode = "production"
    if purpose == "revision":
        plan["q"] = [{"score": 1, "findings": []}]  # forces QUALITY_BLOCK -> revision
    if purpose == "reference":
        mode = "calibration"
    plan[purpose] = [daily_linkedin_author.AuthorLLMError(
        f"Model response was not valid JSON: x\nRaw response: {SENTINEL!r}")]
    return plan, mode


@pytest.mark.parametrize("purpose", PURPOSES)
def test_raw_model_text_never_escapes_from_any_call_site(tmp_path, capsys, monkeypatch, purpose):
    plan, mode = _scenario(purpose)
    if mode == "calibration":
        ref = tmp_path / "reference.md"
        ref.write_text("Эталонный текст.", encoding="utf-8")
        monkeypatch.setenv("HABR_CALIBRATION_REFERENCE_PATH", str(ref))
        env = {"GITHUB_APP_TOKEN": "narrow", "HABR_CALIBRATION_REFERENCE_PATH": str(ref)}
    else:
        env = None
    caller = ScriptedCaller(plan)
    record, out = go(tmp_path, caller=caller, mode=mode, env=env)

    assert any(c["purpose"] == purpose for c in caller.calls), f"{purpose} call site was not reached"
    printed = capsys.readouterr()
    everything = "".join(p.read_text(encoding="utf-8") for p in out.iterdir())
    assert SENTINEL not in printed.out and SENTINEL not in printed.err
    assert SENTINEL not in everything and SENTINEL not in json.dumps(record)
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["failure_kind"] == "execution_error"
    assert "AuthorLLMError" in record["reason"]  # only the class name survives


def test_llm_exception_has_no_chained_raw_text():
    from habr_draft.budget import BudgetGuard
    from habr_draft.llm import HabrLLM, LlmExecutionError, LlmRequest

    def caller(*a, **k):
        raise RuntimeError(f"secret body {SENTINEL}")

    guard = BudgetGuard(limit_usd=10.0, price_in_per_mtok=2.0, price_out_per_mtok=10.0, max_retries=2)
    with pytest.raises(LlmExecutionError) as caught:
        HabrLLM(make_config(), guard, caller=caller).ask(
            LlmRequest(system="s", task="t"), max_tokens=10, purpose="generation")
    error = caught.value
    assert SENTINEL not in str(error) and SENTINEL not in repr(error)
    assert error.__cause__ is None and error.__context__ is None


def test_call_model_is_reached_only_through_the_single_llm_door():
    from pathlib import Path

    package = Path(__file__).resolve().parent
    offenders = []
    for path in sorted(package.glob("*.py")):
        if path.name.startswith("test_") or path.name in ("llm.py", "testsupport.py", "conftest.py"):
            continue
        text = path.read_text(encoding="utf-8")
        if "call_model(" in text or "messages.create" in text:
            offenders.append(path.name)
    assert offenders == []


# ---- calibration ----------------------------------------------------------------


def _calibration_env(tmp_path, text="Эталонная статья владельца."):
    ref = tmp_path / "reference.md"
    ref.write_text(text, encoding="utf-8")
    return {"GITHUB_APP_TOKEN": "narrow", "HABR_CALIBRATION_REFERENCE_PATH": str(ref)}


def test_calibration_records_scores_and_hash_never_ready_and_makes_a_record(tmp_path):
    plan = good_plan()
    caller = ScriptedCaller(plan)
    record, out = go(tmp_path, caller=caller, mode="calibration", env=_calibration_env(tmp_path),
                     config=make_config(q_threshold=None))
    saved = read_record(out)  # an immutable run record exists, like any other run
    assert saved["terminal_outcome"] is None
    assert saved["observable_outcome"] == "CALIBRATION_RECORDED"
    assert saved["calibration_result"] == "recorded"
    assert saved["calibration"]["q_score"] == 90
    ref = saved["calibration"]["reference"]
    assert len(ref["sha256"]) == 64 and ref["length"] == len("Эталонная статья владельца.")
    assert ref["q_score"] == 80
    assert ref["q_findings"] == [{"criterion": "ai_markers", "severity": "minor"}]
    purposes = [c["purpose"] for c in caller.calls]
    assert purposes.count("generation") == 1 and "revision" not in purposes  # one round only
    assert "Эталонная статья владельца." not in json.dumps(saved)  # reference text not persisted
    assert "Calibration run: acceptance was not evaluated" in saved["report"]


def test_calibration_requires_owner_approval_and_reference_before_any_call(tmp_path):
    caller = ScriptedCaller(good_plan())
    record, _ = go(tmp_path, caller=caller, mode="calibration", env={"GITHUB_APP_TOKEN": "narrow"},
                   config=make_config(calibration_approval=None))
    assert caller.calls == []
    assert record["failure_kind"] == "missing_configuration"
    assert "calibration_approval" in record["reason"]
    assert "HABR_CALIBRATION_REFERENCE_PATH" in record["reason"]
    assert record["calibration_result"] == "not_recorded"


def test_calibration_with_secret_in_reference_findings_is_redacted_in_record(tmp_path):
    secret = "gh" + "p_" + "E" * 36
    plan = good_plan()
    plan["reference"] = [{"score": 70, "findings": [{"criterion": f"leak {secret}", "severity": "minor"}]}]
    record, out = go(tmp_path, caller=ScriptedCaller(plan), mode="calibration",
                     env=_calibration_env(tmp_path), config=make_config(q_threshold=None))
    assert secret not in (out / next(p.name for p in out.glob("run_*.json"))).read_text(encoding="utf-8")


# --- failure_kind: input_validation, and configuration before selection -------


class Spy:
    """Counts how often topic selection reached GitHub."""

    def __init__(self, result=None):
        self.fetches, self.visibility_checks = [], []
        self._result = result

    def fetch(self, unit):
        self.fetches.append(unit["repo"])
        return self._result if self._result is not None else fetch_ok(unit)

    def visible(self, repo):
        self.visibility_checks.append(repo)
        return True


INCOMPLETE = {
    "q_threshold": make_config(q_threshold=None),
    "paid_calls_disabled": make_config(paid_calls_enabled=False),
    "no_cleared_repository": make_config(allow_list=[]),
    "owner_identities_unset": make_config(owner_identities=[]),
    "owner_authorization_unset": make_config(owner_authorization=None),
}


@pytest.mark.parametrize("name", sorted(INCOMPLETE))
def test_incomplete_configuration_stops_before_candidate_selection(tmp_path, name):
    spy, caller = Spy(), ScriptedCaller(good_plan())
    record, out = go(tmp_path, config=INCOMPLETE[name], caller=caller,
                     fetch_fn=spy.fetch, visibility=spy.visible)
    assert spy.fetches == [] and spy.visibility_checks == [] and caller.calls == []
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["observable_outcome"] == "SYSTEM_FAILURE"
    assert record["failure_kind"] == "missing_configuration"
    assert record["topic"] is None
    assert read_record(out)["failure_kind"] == "missing_configuration"


def test_incomplete_configuration_is_never_reported_as_no_eligible_topic(tmp_path):
    # Every candidate would come back empty, which on a complete configuration
    # is NO_ELIGIBLE_TOPIC. With the configuration incomplete it must not be.
    spy = Spy(FetchResult())
    record, _ = go(tmp_path, config=make_config(owner_identities=[]),
                   fetch_fn=spy.fetch, visibility=spy.visible)
    assert record["observable_outcome"] != "NO_ELIGIBLE_TOPIC"
    assert record["failure_kind"] == "missing_configuration" and spy.fetches == []
    assert "owner_identities" in record["missing_configuration"]


def test_incomplete_configuration_takes_precedence_over_failed_preflight_and_keeps_it(tmp_path):
    selection = {"status": "failed", "reason": "daily_brief_missing", "detail": "no file",
                 "date": DATE, "daily_brief_sha256": None}
    record, _ = go(tmp_path, selection=selection, config=make_config(q_threshold=None))
    assert record["failure_kind"] == "missing_configuration"
    assert record["preflight"]["reason"] == "daily_brief_missing"


def test_calibration_mode_also_stops_before_selection_on_incomplete_configuration(tmp_path):
    spy, caller = Spy(), ScriptedCaller(good_plan())
    record, _ = go(tmp_path, mode="calibration", config=make_config(allow_list=[]),
                   caller=caller, fetch_fn=spy.fetch, visibility=spy.visible,
                   env={"GITHUB_APP_TOKEN": "n", "HABR_CALIBRATION_REFERENCE_PATH": __file__})
    assert spy.fetches == [] and caller.calls == []
    assert record["failure_kind"] == "missing_configuration"
    assert "allow_list.cleared_repository" in record["missing_configuration"]


@pytest.mark.parametrize("reason", ["daily_brief_schema_unsupported", "daily_brief_malformed",
                                    "daily_brief_unreadable"])
def test_input_validation_is_a_system_failure_that_selects_and_calls_nothing(tmp_path, reason):
    selection = {"status": "failed", "reason": reason,
                 "detail": "schema_version=2, expected 3", "date": DATE, "daily_brief_sha256": "d" * 64}
    spy, caller = Spy(), ScriptedCaller(good_plan())
    record, out = go(tmp_path, selection=selection, caller=caller,
                     fetch_fn=spy.fetch, visibility=spy.visible)
    saved = read_record(out)
    assert spy.fetches == [] and spy.visibility_checks == [] and caller.calls == []
    assert saved["terminal_outcome"] == saved["observable_outcome"] == "SYSTEM_FAILURE"
    assert saved["failure_kind"] == "input_validation"
    assert saved["topic"] is None and saved["rounds"] == []
    assert "not a service outage" in saved["report"]
    assert list(out.glob("attempt_*.md")) == []


def test_no_eligible_topic_only_after_a_clean_walk_of_every_candidate(tmp_path):
    spy = Spy(FetchResult())
    selection = selection_ok()
    selection["units"] += selection_ok("radar")["units"]
    record, _ = go(tmp_path, fetch_fn=spy.fetch, visibility=spy.visible, selection=selection)
    assert record["observable_outcome"] == "NO_ELIGIBLE_TOPIC"
    assert sorted(spy.fetches) == ["article-pipeline", "radar"]  # every candidate was examined
    assert record["failure_kind"] is None and record["terminal_outcome"] is None


def test_visibility_check_that_could_not_run_is_a_technical_error_not_no_eligible_topic(tmp_path):
    record, _ = go(tmp_path, visibility=lambda repo: None, caller=ScriptedCaller(good_plan()))
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["failure_kind"] == "execution_error"
    assert record["observable_outcome"] != "NO_ELIGIBLE_TOPIC"
    assert record["topic"]["walk"][0]["reason"] == "visibility_check_error"


def test_confirmed_not_public_for_every_candidate_is_a_clean_no_eligible_topic(tmp_path):
    record, _ = go(tmp_path, visibility=lambda repo: False)
    assert record["observable_outcome"] == "NO_ELIGIBLE_TOPIC"
    assert record["failure_kind"] is None


def test_stage_1_technical_error_prevents_no_eligible_topic(tmp_path):
    selection = selection_ok()
    selection["units"] = []
    selection["technical_errors"] = [
        {"repo": "radar", "kind": "integrity_unverifiable", "cause": "unverifiable_response"}
    ]
    record, out = go(tmp_path, selection=selection)
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["failure_kind"] == "execution_error" and record["reason"] == "integrity_unverifiable"
    assert read_record(out)["topic"]["stage_1_technical_errors"][0]["repo"] == "radar"


def test_stage_1_technical_error_does_not_block_a_topic_found_among_other_candidates(tmp_path):
    selection = selection_ok()
    selection["technical_errors"] = [
        {"repo": "radar", "kind": "integrity_unverifiable", "cause": "request_failed"}
    ]
    record, _ = go(tmp_path, selection=selection, caller=ScriptedCaller(good_plan()))
    assert record["terminal_outcome"] == "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW"


# --- the selection input crosses a job boundary as an artifact ---------------


@pytest.mark.parametrize("raw, reason", [
    (None, "selection_input_unreadable"),            # artifact missing
    ("{not json", "selection_input_unreadable"),
    ("[1, 2]", "selection_input_malformed"),
    (json.dumps({"status": "ok", "units": "x"}), "selection_input_malformed"),
    (json.dumps({"status": "ok", "units": ["not-a-dict"]}), "selection_input_malformed"),
    (json.dumps({"status": "ok", "units": [{"commit_count": 1, "files_touched": [],
                                            "commit_messages": []}]}), "selection_input_malformed"),
    (json.dumps({"status": "ok", "units": [{"repo": "r", "commit_count": 1, "files_touched": [],
                                            "commit_messages": ["x"]}]}), "selection_input_malformed"),
])
def test_unreadable_or_malformed_selection_artifact_is_input_validation_not_a_crash(
        tmp_path, raw, reason):
    path = tmp_path / "selection_input.json"
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    spy, caller = Spy(), ScriptedCaller(good_plan())
    out = tmp_path / "out"
    record = run_habr_draft.run(
        selection_path=path, date=DATE, mode="production", output_dir=out, config=make_config(),
        env={"GITHUB_APP_TOKEN": "narrow"}, caller=caller, fetch_fn=spy.fetch, visibility=spy.visible,
    )
    assert record["terminal_outcome"] == "SYSTEM_FAILURE"
    assert record["failure_kind"] == "input_validation"
    assert record["reason"].startswith(reason)
    assert spy.fetches == [] and caller.calls == []
    assert len(list(out.glob("run_*.json"))) == 1  # the record is still written


# --- what stage 2 really writes is what the deliver gate accepts -------------


def test_every_outcome_stage_2_writes_passes_the_deliver_gate(tmp_path):
    from habr_draft import deliver

    plan = good_plan()
    plan["q"] = [{"score": 10, "findings": [{"criterion": "ai_markers", "severity": "major"}]}]
    scenarios = {
        "ready": dict(caller=ScriptedCaller(good_plan())),
        "blocked_with_three_attempts": dict(caller=ScriptedCaller(plan)),
        "missing_configuration": dict(config=make_config(q_threshold=None)),
        "no_eligible_topic": dict(visibility=lambda r: False),
        "calibration": dict(mode="calibration", caller=ScriptedCaller(good_plan()),
                            env={"GITHUB_APP_TOKEN": "n", "HABR_CALIBRATION_REFERENCE_PATH": __file__}),
    }
    for name, kwargs in scenarios.items():
        base = tmp_path / name
        base.mkdir()
        record, out = go(base, **kwargs)
        staged = deliver.stage(out, base / "registry" / "output" / "habr_draft" / "1")
        assert f"run_{record['run_id']}.json" in staged, name


# --- volume cap: a candidate left with no fragment is not a usable topic -----


def test_candidate_whose_fragments_all_exceed_the_cap_is_skipped_without_paid_calls(tmp_path):
    big = FetchResult(fragments=[{**fetch_ok({"repo": "article-pipeline"}).fragments[0],
                                  "content": "x" * 500}])
    config = make_config(budget=make_config().budget.model_copy(
        update={"max_fragment_chars_per_attempt": 100}))
    caller = ScriptedCaller(good_plan())
    record, out = go(tmp_path, config=config, caller=caller, fetch_fn=lambda unit: big)
    assert caller.calls == []
    assert record["observable_outcome"] == "NO_ELIGIBLE_TOPIC"
    walk = record["topic"]["walk"]
    assert len(walk) == 1 and walk[0]["repo"] == "article-pipeline"
    assert {e["reason"] for e in walk[0]["exclusions"]} == {"volume_cap"}


def test_calibration_reference_that_cannot_be_read_is_missing_configuration_not_a_crash(tmp_path):
    bad = tmp_path / "ref.md"
    bad.write_bytes(b"\xff\xfe\x00bad")
    record, out = go(tmp_path, mode="calibration", caller=ScriptedCaller(good_plan()),
                     env={"GITHUB_APP_TOKEN": "n", "HABR_CALIBRATION_REFERENCE_PATH": str(bad)})
    assert record["failure_kind"] == "missing_configuration"
    assert "HABR_CALIBRATION_REFERENCE_PATH" in record["missing_configuration"]


def test_cap_drops_on_the_chosen_candidate_are_recorded_as_dropped_not_excluded(tmp_path):
    frag = fetch_ok({"repo": "article-pipeline"}).fragments[0]
    two = FetchResult(fragments=[frag, {**frag, "id": "article-pipeline:frag_02",
                                        "path": "src/big.py", "content": "y" * 500}])
    config = make_config(budget=make_config().budget.model_copy(
        update={"max_fragment_chars_per_attempt": 200}))
    record, out = go(tmp_path, config=config, caller=ScriptedCaller(good_plan()),
                     fetch_fn=lambda unit: two)
    saved = read_record(out)
    assert [f["path"] for f in saved["fragments"]["used"]] == ["src/build.py"]
    assert [d["path"] for d in saved["fragments"]["dropped"]] == ["src/big.py"]
    assert all(e["reason"] != "volume_cap" for e in saved["fragments"]["excluded"])
