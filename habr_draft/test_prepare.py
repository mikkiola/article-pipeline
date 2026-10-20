import json

import collector
import pytest

from habr_draft import prepare
from habr_draft.config import AllowListEntry
from habr_draft.testsupport import make_config

DATE = "2026-10-15"
REPOS = ["archi-kg", "article-pipeline", "brain", "collector", "radar", "radar-vault", "tooltempest"]


def brief(date=DATE, schema=3):
    messages = {
        "article-pipeline": ["feat: compute in build"],
        "radar": ["fix: radar thing"],
        "brain": ["feat: private brain change"],
        "radar-vault": ["notes: vault entry"],
    }
    commits = [
        {"repo": repo, "sha": f"{i}{j}".ljust(40, "0"), "subject": subject, "why": None, "effect": None}
        for i, (repo, subjects) in enumerate(messages.items())
        for j, subject in enumerate(subjects)
    ]
    return {
        "schema_version": schema, "mode": "fact", "date": date, "window": "1.day",
        "total_diffstat": 10, "files_touched": [], "commit_messages": commits,
        "per_repo": [
            {"name": repo, "branch": "vault" if repo == "radar-vault" else "main",
             "head_sha": "f" * 40, "commit_count": len(messages.get(repo, [])),
             "diffstat": 5, "files_touched": [f"{repo}.py"] if repo in messages else []}
            for repo in REPOS
        ],
        "decision_source": "heuristic",
    }


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_TOKEN", "broad-token")
    monkeypatch.setattr(collector, "check_integrity", lambda *a, **k: ("valid", "mocked"))


def write(tmp_path, content):
    path = tmp_path / "daily_brief.json"
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return path


def test_only_allow_listed_cleared_main_branch_units_cross_the_boundary(tmp_path):
    result = prepare.prepare(write(tmp_path, brief()), DATE, make_config())
    assert result["status"] == "ok"
    assert sorted(u["repo"] for u in result["units"]) == ["article-pipeline", "radar"]
    names = json.dumps(result["units"])
    assert "private brain change" not in names and "vault entry" not in names
    reasons = {e["repo"]: e["reason"] for e in result["excluded"]}
    assert reasons["brain"] == "not_allow_listed_or_wrong_branch"
    assert reasons["radar-vault"] == "not_allow_listed_or_wrong_branch"


def test_unit_carries_commit_shas_from_the_raw_brief(tmp_path):
    result = prepare.prepare(write(tmp_path, brief()), DATE, make_config())
    unit = next(u for u in result["units"] if u["repo"] == "article-pipeline")
    assert unit["commit_messages"][0]["subject"] == "feat: compute in build"
    assert len(unit["commit_messages"][0]["sha"]) == 40


def test_uncleared_source_does_not_cross(tmp_path):
    cfg = make_config(allow_list=[
        AllowListEntry(repo="article-pipeline", branch="main", content_safety_checked=True,
                       authorship_checked=False)])
    result = prepare.prepare(write(tmp_path, brief()), DATE, cfg)
    assert result["units"] == []
    assert any(e["reason"] == "source_not_cleared" for e in result["excluded"])


@pytest.mark.parametrize("content,reason", [
    (None, "daily_brief_missing"),
    ("{not json", "daily_brief_malformed"),
    ("[]", "daily_brief_malformed"),
])
def test_expected_input_failures_return_a_structured_result_not_an_exception(tmp_path, content, reason):
    path = tmp_path / "missing.json" if content is None else write(tmp_path, content)
    result = prepare.prepare(path, DATE, make_config())
    assert result["status"] == "failed" and result["reason"] == reason


def test_wrong_date_and_unsupported_schema_are_failures(tmp_path):
    wrong_date = prepare.prepare(write(tmp_path, brief(date="2026-10-14")), DATE, make_config())
    assert wrong_date["reason"] == "daily_brief_date_mismatch"
    old = prepare.prepare(write(tmp_path, brief(schema=2)), DATE, make_config())
    assert old["reason"] == "daily_brief_schema_unsupported"


def test_missing_token_is_a_specific_preflight_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_APP_TOKEN")
    result = prepare.prepare(write(tmp_path, brief()), DATE, make_config())
    assert result["status"] == "failed" and result["reason"] == "github_token_missing"


def test_main_exits_zero_and_writes_the_failure_result(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out" / "selection_input.json"
    monkeypatch.setattr("sys.argv", ["prepare", "--daily-brief-path", str(tmp_path / "nope.json"),
                                     "--date", DATE, "--out", str(out)])
    prepare.main()  # must not raise SystemExit / exception
    assert json.loads(out.read_text())["reason"] == "daily_brief_missing"


# --- technical integrity failures are not verdicts ---------------------------

REAL_CHECK_INTEGRITY = collector.check_integrity  # captured before the autouse patch


def _integrity_detail(monkeypatch, *, status=200, body=None, raises=False, token="broad"):
    if token is None:
        monkeypatch.delenv("GITHUB_APP_TOKEN", raising=False)

    def getter(path, tok):
        if raises:
            raise OSError("connection reset")
        return status, body
    monkeypatch.setattr(collector, "_github_get", getter)
    verdict, detail = REAL_CHECK_INTEGRITY("radar", "main", "f" * 40)
    assert verdict == "invalid"
    return detail


@pytest.mark.parametrize("kwargs,cause", [
    ({"raises": True}, "request_failed"),
    ({"status": 500}, "unverifiable_response"),
    ({"status": 403}, "unverifiable_response"),
    ({"status": 429}, "unverifiable_response"),
    ({"status": 404}, "unverifiable_response"),
    ({"token": None}, "token_missing"),
])
def test_real_check_integrity_failures_to_ask_are_classified_as_technical(monkeypatch, kwargs, cause):
    detail = _integrity_detail(monkeypatch, **kwargs)
    assert prepare.integrity_unverifiable_cause(detail) == cause


@pytest.mark.parametrize("body", [
    {"status": "behind", "behind_by": 3, "ahead_by": 0},
    {"status": "diverged", "behind_by": 1, "ahead_by": 1},
])
def test_a_definite_not_an_ancestor_answer_is_a_verdict_not_a_technical_error(monkeypatch, body):
    detail = _integrity_detail(monkeypatch, status=200, body=body)
    assert prepare.integrity_unverifiable_cause(detail) is None


def test_missing_head_sha_record_is_a_verdict_about_the_record():
    verdict, detail = REAL_CHECK_INTEGRITY("radar", "main", None)
    assert verdict == "invalid" and prepare.integrity_unverifiable_cause(detail) is None


def test_prepare_reports_unverifiable_allow_listed_repos_as_technical_errors(tmp_path, monkeypatch):
    def getter(path, tok):
        return (503, None) if "/radar/" in path else (
            200, {"status": "identical", "behind_by": 0, "ahead_by": 0})
    monkeypatch.setattr(collector, "check_integrity", REAL_CHECK_INTEGRITY)
    monkeypatch.setattr(collector, "_github_get", getter)
    result = prepare.prepare(write(tmp_path, brief()), DATE, make_config())
    assert [u["repo"] for u in result["units"]] == ["article-pipeline"]
    assert result["technical_errors"] == [
        {"repo": "radar", "kind": "integrity_unverifiable", "cause": "unverifiable_response"}]


def test_prepare_ignores_unverifiable_repos_that_are_not_allow_listed(tmp_path, monkeypatch):
    def getter(path, tok):
        return (503, None) if "/brain/" in path else (
            200, {"status": "identical", "behind_by": 0, "ahead_by": 0})
    monkeypatch.setattr(collector, "check_integrity", REAL_CHECK_INTEGRITY)
    monkeypatch.setattr(collector, "_github_get", getter)
    result = prepare.prepare(write(tmp_path, brief()), DATE, make_config())
    assert result["technical_errors"] == []


def test_prepare_with_a_clean_verdict_has_no_technical_errors(tmp_path):
    result = prepare.prepare(write(tmp_path, brief()), DATE, make_config())
    assert result["technical_errors"] == []


@pytest.mark.parametrize("section,key,value", [
    ("commit_messages", "repo", []),
    ("commit_messages", "sha", None),
    ("commit_messages", "subject", None),
    ("commit_messages", "why", {}),
    ("commit_messages", "effect", []),
    ("per_repo", "name", []),
    ("per_repo", "branch", []),
    ("per_repo", "head_sha", 42),
    ("per_repo", "commit_count", "1"),
    ("per_repo", "commit_count", True),
    ("per_repo", "diffstat", -1),
    ("per_repo", "files_touched", "file.py"),
    ("per_repo", "files_touched", [None]),
])
def test_malformed_nested_fields_fail_before_adapter_without_echoing_input(
        tmp_path, monkeypatch, section, key, value):
    data = brief()
    data[section][0][key] = value
    data["commit_messages"][0]["subject"] = "PRIVATE-CONTENT-SENTINEL"
    if key == "subject":
        data[section][0][key] = value
    def must_not_adapt(*args):
        pytest.fail("malformed input reached adapter")
    monkeypatch.setattr(collector, "adapt_daily_brief", must_not_adapt)
    result = prepare.prepare(write(tmp_path, data), DATE, make_config())
    assert result["status"] == "failed" and result["reason"] == "daily_brief_malformed"
    assert "PRIVATE-CONTENT-SENTINEL" not in json.dumps(result)


def test_unreadable_brief_is_a_structured_failure(tmp_path, monkeypatch):
    path = write(tmp_path, brief())
    def unreadable(self):
        raise PermissionError("PRIVATE-CONTENT-SENTINEL")
    monkeypatch.setattr(type(path), "read_bytes", unreadable)
    result = prepare.prepare(path, DATE, make_config())
    assert result["status"] == "failed" and result["reason"] == "daily_brief_unreadable"
    assert "PRIVATE-CONTENT-SENTINEL" not in json.dumps(result)
