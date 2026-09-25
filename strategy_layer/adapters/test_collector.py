"""Tests for strategy_layer/adapters/collector.py — Collector's
CanonicalUnit adapter and its ancestry-based integrity check.

TDD per docs/CONSTITUTION.md: check_integrity() is a "does this actually
trigger" gate mechanism. It asks the GitHub REST API whether the branch-tip
SHA Collector recorded at scan time (`head_sha`) is an ancestor of, or equal
to, the branch's current tip: GET /repos/{owner}/{repo}/compare/{head_sha}...
{branch}, valid iff behind_by == 0 (status "identical" or "ahead").

The HTTP layer (`collector._github_get`) is mocked — these tests verify
check_integrity()'s own logic (the right request, the right verdict per
response), not GitHub's behavior. The compare endpoint's real responses were
probed live on 2026-09-25 (ahead / identical / diverged / 404).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collector  # noqa: E402

SHA = "a" * 40


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("GITHUB_APP_TOKEN", "test-token")


def _compare(status, behind_by, ahead_by=0):
    return (200, {"status": status, "behind_by": behind_by, "ahead_by": ahead_by})


# --- check_integrity: the five GitHub compare outcomes -------------------


@patch("collector._github_get")
def test_check_integrity_valid_when_identical(mock_get):
    mock_get.return_value = _compare("identical", 0, 0)
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "valid"
    assert SHA[:12] in detail
    assert "identical" in detail


@patch("collector._github_get")
def test_check_integrity_valid_when_branch_is_ahead_of_head_sha(mock_get):
    # The branch moved on after the scan: head_sha is an ancestor of the tip.
    mock_get.return_value = _compare("ahead", 0, 3)
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "valid"
    assert "ahead" in detail


@patch("collector._github_get")
def test_check_integrity_invalid_when_behind(mock_get):
    mock_get.return_value = _compare("behind", 2, 0)
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "invalid"
    assert "behind" in detail


@patch("collector._github_get")
def test_check_integrity_invalid_when_diverged(mock_get):
    # head_sha exists but lives on some other branch's history.
    mock_get.return_value = _compare("diverged", 4, 5)
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "invalid"
    assert "diverged" in detail


@patch("collector._github_get")
def test_check_integrity_invalid_on_404(mock_get):
    # Nonexistent SHA, repo, or branch — GitHub answers 404 for all three.
    mock_get.return_value = (404, None)
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "invalid"
    assert "404" in detail


# --- check_integrity: fail-closed on everything else ---------------------


@patch("collector._github_get")
def test_check_integrity_invalid_on_other_http_error(mock_get):
    mock_get.return_value = (403, None)  # e.g. token lacks access / rate limit
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "invalid"
    assert "403" in detail


@patch("collector._github_get")
def test_check_integrity_invalid_when_the_request_raises(mock_get):
    mock_get.side_effect = OSError("network unreachable")
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "invalid"
    assert "network unreachable" in detail


@patch("collector._github_get")
def test_check_integrity_invalid_without_a_token_and_makes_no_request(mock_get, monkeypatch):
    monkeypatch.delenv("GITHUB_APP_TOKEN", raising=False)
    status, detail = collector.check_integrity("collector", "main", SHA)
    assert status == "invalid"
    assert "GITHUB_APP_TOKEN" in detail
    mock_get.assert_not_called()


@patch("collector._github_get")
def test_check_integrity_invalid_without_head_sha_and_makes_no_request(mock_get):
    for missing in (None, ""):
        status, detail = collector.check_integrity("collector", "main", missing)
        assert status == "invalid"
        assert "head_sha" in detail
    mock_get.assert_not_called()


@patch("collector._github_get")
def test_check_integrity_invalid_without_branch_and_makes_no_request(mock_get):
    status, detail = collector.check_integrity("collector", None, SHA)
    assert status == "invalid"
    assert "branch" in detail
    mock_get.assert_not_called()


# --- check_integrity: what is asked of the API ---------------------------


@patch("collector._github_get")
def test_check_integrity_asks_the_compare_endpoint_with_head_sha_then_branch(mock_get):
    mock_get.return_value = _compare("identical", 0)
    collector.check_integrity("collector", "main", SHA)
    path, token = mock_get.call_args.args[0], mock_get.call_args.args[1]
    assert path.startswith(f"/repos/mikkiola/collector/compare/{SHA}...main")
    assert token == "test-token"


@patch("collector._github_get")
def test_check_integrity_maps_radar_vault_to_the_radar_repo_only_for_the_api_call(mock_get):
    mock_get.return_value = _compare("identical", 0)
    collector.check_integrity("radar-vault", "vault", SHA)
    path = mock_get.call_args.args[0]
    assert path.startswith(f"/repos/mikkiola/radar/compare/{SHA}...vault")


@patch("collector._github_get")
def test_check_integrity_does_not_touch_the_local_filesystem_or_git(mock_get):
    # The whole point of the API check: no local checkout is needed, so a
    # repo that exists nowhere on disk is still verifiable.
    mock_get.return_value = _compare("identical", 0)
    with patch("collector.Path.is_dir", side_effect=AssertionError("local FS consulted")):
        status, _ = collector.check_integrity("some-repo-not-on-disk", "main", SHA)
    assert status == "valid"
    assert not hasattr(collector, "_run_git")


# --- adapt_daily_brief ---------------------------------------------------


def _brief(**overrides):
    brief = {
        "schema_version": 2,
        "mode": "fact",
        "date": "2026-09-24",
        "window": "1.day",
        "total_diffstat": 100,
        "files_touched": ["a.py"],
        "commit_messages": [
            {"repo": "article-pipeline", "sha": "1" * 40, "subject": "feat(a): change in article-pipeline"},
            {"repo": "article-pipeline", "sha": "2" * 40, "subject": "fix(a): second in article-pipeline"},
            {"repo": "radar", "sha": "3" * 40, "subject": "Radar update"},
            {"repo": "collector", "sha": "4" * 40, "subject": "chore(data): daily run"},
        ],
        "per_repo": [
            {"name": "article-pipeline", "branch": "main", "head_sha": "a" * 40,
             "commit_count": 2, "diffstat": 60, "files_touched": ["a.py"]},
            {"name": "radar", "branch": "main", "head_sha": "b" * 40,
             "commit_count": 1, "diffstat": 20, "files_touched": ["r.md"]},
            {"name": "collector", "branch": "main", "head_sha": "c" * 40,
             "commit_count": 1, "diffstat": 20, "files_touched": ["d.json"]},
            {"name": "brain", "branch": "main", "head_sha": "d" * 40,
             "commit_count": 0, "diffstat": 0, "files_touched": []},
        ],
        "decision_source": "heuristic",
    }
    brief.update(overrides)
    return brief


def test_adapt_daily_brief_produces_one_unit_per_repo_and_verifies_each_head_sha():
    calls = []

    def fake_check(repo_name, branch, head_sha):
        calls.append((repo_name, branch, head_sha))
        return "valid", "mocked"

    with patch("collector.check_integrity", side_effect=fake_check):
        units = collector.adapt_daily_brief(_brief())

    assert [u.metadata["repo"] for u in units] == ["article-pipeline", "radar", "collector", "brain"]
    assert calls == [
        ("article-pipeline", "main", "a" * 40),
        ("radar", "main", "b" * 40),
        ("collector", "main", "c" * 40),
        ("brain", "main", "d" * 40),
    ]
    assert units[0].integrity_check_method == "ancestry_reconciliation"
    assert units[0].corroboration_status == "not_applicable"
    assert units[0].metadata["branch"] == "main"
    assert units[0].metadata["head_sha"] == "a" * 40
    assert units[0].metadata["commit_count"] == 2
    assert units[0].metadata["source_type"] == "collector_daily_brief"


def test_a_unit_receives_only_its_own_repos_commit_messages():
    with patch("collector.check_integrity", return_value=("valid", "mocked")):
        units = collector.adapt_daily_brief(_brief())
    by_repo = {u.metadata["repo"]: u.metadata["commit_messages"] for u in units}

    assert by_repo["article-pipeline"] == [
        "feat(a): change in article-pipeline",
        "fix(a): second in article-pipeline",
    ]
    assert by_repo["radar"] == ["Radar update"]
    assert by_repo["collector"] == ["chore(data): daily run"]
    assert by_repo["brain"] == []


def test_an_invalid_unit_is_still_built_with_its_own_slice_only():
    def fake_check(repo_name, branch, head_sha):
        return ("invalid", "nope") if repo_name == "radar" else ("valid", "mocked")

    with patch("collector.check_integrity", side_effect=fake_check):
        units = collector.adapt_daily_brief(_brief())
    radar = next(u for u in units if u.metadata["repo"] == "radar")
    assert radar.integrity_status == "invalid"
    assert radar.metadata["commit_messages"] == ["Radar update"]


def test_a_brief_of_an_unknown_schema_version_is_invalid_and_calls_no_api():
    old_shape = _brief()
    del old_shape["schema_version"]
    with patch("collector._github_get") as mock_get:
        units = collector.adapt_daily_brief(old_shape)
    assert len(units) == 4
    assert all(u.integrity_status == "invalid" for u in units)
    assert "schema_version" in units[0].metadata["integrity_check_detail"]
    assert all(u.metadata["commit_messages"] == [] for u in units)
    mock_get.assert_not_called()


def test_a_malformed_commit_message_entry_is_refused_loudly():
    bad = _brief(commit_messages=["a bare string, the old flat shape"])
    with patch("collector.check_integrity", return_value=("valid", "mocked")):
        with pytest.raises(ValueError, match="commit_messages"):
            collector.adapt_daily_brief(bad)


def test_adapt_daily_brief_has_no_local_git_dependency():
    assert not hasattr(collector, "resolve_current_branch")
    assert not hasattr(collector, "parse_window_days")


# --- adapt_manifest: the same shared check --------------------------------


def _manifest():
    return {
        "scan_timestamp": "2026-09-19T00:53:41+00:00",
        "window_days": 7,
        "repos": [
            {"name": "article-pipeline", "branch": "main", "head_sha": "a" * 40,
             "commit_count": 6, "counts": {"value": 2}},
            {"name": "radar-vault", "branch": "vault", "head_sha": "b" * 40,
             "commit_count": 0, "counts": {}},
        ],
    }


def test_adapt_manifest_uses_the_same_check_with_branch_and_head_sha():
    calls = []

    def fake_check(repo_name, branch, head_sha):
        calls.append((repo_name, branch, head_sha))
        return "valid", "mocked"

    with patch("collector.check_integrity", side_effect=fake_check):
        units = collector.adapt_manifest(_manifest())

    assert calls == [("article-pipeline", "main", "a" * 40), ("radar-vault", "vault", "b" * 40)]
    assert units[0].integrity_check_method == "ancestry_reconciliation"
    assert units[0].integrity_status == "valid"
    assert units[0].corroboration_status == "not_applicable"
    assert units[0].assertion_text is None
    assert units[0].metadata["head_sha"] == "a" * 40
    assert units[0].metadata["source_type"] == "collector_manifest"
    assert "commit_messages" not in units[0].metadata


def test_adapt_manifest_record_without_head_sha_is_invalid_without_an_api_call():
    manifest = _manifest()
    del manifest["repos"][0]["head_sha"]  # a manifest written before head_sha existed
    with patch("collector._github_get", return_value=_compare("identical", 0)) as mock_get:
        units = collector.adapt_manifest(manifest)
    assert units[0].integrity_status == "invalid"
    assert "head_sha" in units[0].metadata["integrity_check_detail"]
    # Only the second repo (which still has a head_sha) reached the API.
    assert mock_get.call_count == 1
    assert units[1].integrity_status == "valid"
