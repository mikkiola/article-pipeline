import json

import pytest

from habr_draft import run_record, secret_scan


def test_scan_reports_pattern_ids_and_counts_never_matched_text():
    secret = "gh" + "p_" + "B" * 36
    hits = secret_scan.scan(f"token={secret} and again {secret}")
    assert hits == [{"pattern_id": "github-token", "count": 2}]
    assert secret not in json.dumps(hits)


def test_scan_uses_project_gitleaks_rules():
    ids = set(secret_scan.load_patterns())
    assert "gitleaks:anthropic-api-key" in ids and "gitleaks:local-fs-path" in ids


def test_scan_clean_text_has_no_hits():
    assert secret_scan.scan("def f():\n    return 1\n") == []


def test_scan_that_cannot_load_rules_is_an_error(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("this is = not [valid", encoding="utf-8")
    with pytest.raises(secret_scan.SecretScanError):
        secret_scan.load_patterns(bad)


def test_files_are_immutable(tmp_path):
    run_record.write_attempt(tmp_path, 1, "T", "body")
    with pytest.raises(FileExistsError):
        run_record.write_attempt(tmp_path, 1, "T", "other body")
    assert "body" in (tmp_path / "attempt_1.md").read_text(encoding="utf-8")
    run_record.write_run_record(tmp_path, "r1", {"a": 1})
    with pytest.raises(FileExistsError):
        run_record.write_run_record(tmp_path, "r1", {"a": 2})


def test_attempt_file_hash_matches_content(tmp_path):
    import hashlib
    info = run_record.write_attempt(tmp_path, 2, "T", "body")
    assert info["sha256"] == hashlib.sha256((tmp_path / info["name"]).read_bytes()).hexdigest()


def test_run_record_redacts_secret_strings_in_findings(tmp_path):
    secret = "gh" + "p_" + "C" * 36
    run_record.write_run_record(tmp_path, "r2", {"rounds": [{"findings": [{"note": f"see {secret}"}]}]})
    text = (tmp_path / "run_r2.json").read_text(encoding="utf-8")
    assert secret not in text and "redacted" in text


def test_report_never_reads_as_publication_approval():
    for outcome in (None, "BLOCKED", "SYSTEM_FAILURE", "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW"):
        assert run_record.NOT_APPROVAL_STATEMENT in run_record.build_report(outcome, "production", None)
    ready = run_record.build_report("INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW", "production", None)
    assert "rule 4" in ready and "rule 1" in ready and "topic and format" in ready


def test_missing_configuration_is_reported_as_such_not_as_outage():
    text = run_record.build_report("SYSTEM_FAILURE", "production", "missing_configuration")
    assert "missing configuration, not a service outage" in text


def test_output_dir_requires_the_environment_variable(monkeypatch):
    monkeypatch.delenv(run_record.OUTPUT_DIR_ENV, raising=False)
    with pytest.raises(RuntimeError):
        run_record.output_dir_from_env()


# --- failure_kind schema ----------------------------------------------------


@pytest.mark.parametrize("kind", ["missing_configuration", "execution_error", "budget_limit",
                                  "input_validation"])
def test_every_failure_kind_serializes_inside_system_failure(tmp_path, kind):
    record = {"run_id": f"r-{kind}", "terminal_outcome": "SYSTEM_FAILURE",
              "observable_outcome": "SYSTEM_FAILURE", "failure_kind": kind}
    written = run_record.write_run_record(tmp_path, record["run_id"], record)
    saved = json.loads((tmp_path / written["name"]).read_text(encoding="utf-8"))
    assert saved["failure_kind"] == kind and saved["terminal_outcome"] == "SYSTEM_FAILURE"


def test_failure_kinds_are_exactly_the_four_documented_ones():
    assert set(run_record.FAILURE_KINDS) == {
        "missing_configuration", "execution_error", "budget_limit", "input_validation"}


@pytest.mark.parametrize("terminal,kind", [
    ("PUBLISHED", None),                     # unknown terminal outcome
    ("SYSTEM_FAILURE", "outage"),            # unknown kind
    ("SYSTEM_FAILURE", None),                # SYSTEM_FAILURE must say which
    (None, "input_validation"),              # a kind outside SYSTEM_FAILURE
    ("BLOCKED", "execution_error"),
    ("INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW", "budget_limit"),
])
def test_invalid_outcome_kind_combinations_are_refused_and_nothing_is_written(tmp_path, terminal, kind):
    with pytest.raises(ValueError):
        run_record.write_run_record(
            tmp_path, "bad", {"run_id": "bad", "terminal_outcome": terminal, "failure_kind": kind})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("terminal,kind", [
    (None, None), ("BLOCKED", None), ("INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW", None),
])
def test_outcomes_without_a_failure_kind_are_accepted(terminal, kind):
    run_record.validate_outcome(terminal, kind)


def test_input_validation_is_reported_as_neither_outage_nor_quality_failure():
    text = run_record.build_report("SYSTEM_FAILURE", "production", "input_validation")
    assert "failed validation" in text and "not a service outage" in text
    assert "not a quality failure" in text


def test_notification_names_the_input_validation_kind():
    from habr_draft import notify
    message = notify.build_message(
        {"run_id": "r1", "observable_outcome": "SYSTEM_FAILURE", "failure_kind": "input_validation",
         "reason": "daily_brief_missing: no file"}, "ref")
    assert "failure_kind: input_validation" in message
