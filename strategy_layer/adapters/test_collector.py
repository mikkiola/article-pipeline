"""Tests for strategy_layer/adapters/collector.py — Collector's
CanonicalUnit adapter, including its real integrity check (SPEC.md's
Non-Functional Requirement 1, TDD required: "does this actually
trigger" under specific repo/branch/commit-count conditions is the
central risk, same class as the gate-check).

git subprocess calls are mocked (unittest.mock.patch), same precedent
as this project's existing test-reconcile scripts — these tests verify
check_integrity()'s own logic (the right git args, the right verdict
per outcome), not real git behavior. A separate, unmocked real run
against this workspace's actual repos is done outside this test file
and reported directly (SPEC.md's Test Plan real-data-run convention).
"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collector  # noqa: E402


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


ANCHOR = datetime(2026, 9, 12, 0, 50, 24, tzinfo=timezone.utc)


def test_parse_window_days_singular():
    assert collector.parse_window_days("1.day") == 1


def test_parse_window_days_plural():
    assert collector.parse_window_days("7.days") == 7


def test_parse_window_days_invalid_raises():
    with pytest.raises(ValueError, match="cannot parse"):
        collector.parse_window_days("not-a-window")


@patch("collector.Path.is_dir", return_value=False)
def test_check_integrity_invalid_when_repo_missing(mock_is_dir):
    status, detail = collector.check_integrity("nonexistent-repo", "main", 5, 7, ANCHOR)
    assert status == "invalid"
    assert "not found" in detail


@patch("collector.Path.is_dir", return_value=True)
@patch("collector._run_git")
def test_check_integrity_invalid_when_branch_missing(mock_run_git, mock_is_dir):
    mock_run_git.return_value = _completed(returncode=1, stderr="fatal: not a valid ref")
    status, detail = collector.check_integrity("article-pipeline", "nonexistent-branch", 5, 7, ANCHOR)
    assert status == "invalid"
    assert "not found" in detail


@patch("collector.Path.is_dir", return_value=True)
@patch("collector._run_git")
def test_check_integrity_valid_when_count_matches(mock_run_git, mock_is_dir):
    # First call: rev-parse --verify (branch exists) -> success.
    # Second call: rev-list --count (reconciliation) -> matches reported.
    mock_run_git.side_effect = [
        _completed(returncode=0, stdout="abc123\n"),
        _completed(returncode=0, stdout="6\n"),
    ]
    status, detail = collector.check_integrity("article-pipeline", "main", 6, 7, ANCHOR)
    assert status == "valid"
    assert "reconciled: 6" in detail
    assert "matched reported 6" in detail


@patch("collector.Path.is_dir", return_value=True)
@patch("collector._run_git")
def test_check_integrity_invalid_when_count_mismatches(mock_run_git, mock_is_dir):
    mock_run_git.side_effect = [
        _completed(returncode=0, stdout="abc123\n"),
        _completed(returncode=0, stdout="4\n"),
    ]
    status, detail = collector.check_integrity("article-pipeline", "main", 6, 7, ANCHOR)
    assert status == "invalid"
    assert "mismatch" in detail
    assert "reported=6" in detail
    assert "reconciled=4" in detail


@patch("collector.Path.is_dir", return_value=True)
@patch("collector._run_git")
def test_check_integrity_uses_anchored_window_not_now(mock_run_git, mock_is_dir):
    mock_run_git.side_effect = [
        _completed(returncode=0, stdout="abc123\n"),
        _completed(returncode=0, stdout="6\n"),
    ]
    collector.check_integrity("article-pipeline", "main", 6, 7, ANCHOR)

    # Second call is the rev-list reconciliation — confirm BOTH bounds are
    # absolute timestamps anchored to `anchor`, not git's relative
    # --since=N.days shorthand (which resolves against real wall-clock
    # "now", not against --until — confirmed as a real bug via a live run,
    # see check_integrity()'s docstring).
    rev_list_call = mock_run_git.call_args_list[1]
    str_args = [a for a in rev_list_call.args if isinstance(a, str)]
    assert "rev-list" in str_args
    assert "--count" in str_args
    since_arg = next(a for a in str_args if a.startswith("--since="))
    until_arg = next(a for a in str_args if a.startswith("--until="))
    assert "2026-09-05" in since_arg  # ANCHOR (2026-09-12) minus 7 days
    assert "2026-09-12" in until_arg


def test_adapt_manifest_produces_one_unit_per_repo():
    manifest = {
        "scan_timestamp": "2026-09-12T00:50:24.808627+00:00",
        "window_days": 7,
        "repos": [
            {"name": "article-pipeline", "branch": "main", "commit_count": 6, "counts": {"value": 2}},
            {"name": "brain", "branch": "main", "commit_count": 5, "counts": {"value": 5}},
        ],
    }
    with patch("collector.check_integrity", return_value=("valid", "mocked")):
        units = collector.adapt_manifest(manifest)

    assert len(units) == 2
    assert units[0].source == "collector"
    assert units[0].integrity_status == "valid"
    assert units[0].integrity_check_method == "commit_count_reconciliation"
    assert units[0].corroboration_status == "not_applicable"
    assert units[0].assertion_text is None
    assert units[0].metadata["repo"] == "article-pipeline"
    assert units[0].metadata["branch"] == "main"
    assert units[0].metadata["commit_count"] == 6


def test_adapt_manifest_invalid_repo_still_produces_a_unit():
    manifest = {
        "scan_timestamp": "2026-09-12T00:50:24.808627+00:00",
        "window_days": 7,
        "repos": [
            {"name": "ghost-repo", "branch": "main", "commit_count": 3, "counts": {}},
        ],
    }
    with patch("collector.check_integrity", return_value=("invalid", "local checkout not found")):
        units = collector.adapt_manifest(manifest)

    assert len(units) == 1
    assert units[0].integrity_status == "invalid"
    # Excluding-vs-including is pre_filter's job, not the adapter's —
    # the adapter's only responsibility is an honest, complete unit.


def test_adapt_daily_brief_produces_one_unit_per_repo_and_resolves_branch_live():
    daily_brief = {
        "mode": "idea_fallback",
        "date": "2026-09-11",
        "window": "1.day",
        "total_diffstat": 10,
        "files_touched": ["a.py"],
        "commit_messages": ["fix: bug"],
        "per_repo": [
            {"name": "article-pipeline", "commit_count": 2, "diffstat": 10, "files_touched": ["a.py"]},
        ],
        "decision_source": "heuristic",
    }
    with patch("collector.resolve_current_branch", return_value="main"), patch(
        "collector.check_integrity", return_value=("valid", "mocked")
    ):
        units = collector.adapt_daily_brief(daily_brief)

    assert len(units) == 1
    assert units[0].metadata["branch"] == "main"
    assert units[0].metadata["commit_count"] == 2
    assert units[0].corroboration_status == "not_applicable"


def test_adapt_daily_brief_unresolvable_branch_marks_invalid_without_crashing():
    daily_brief = {
        "mode": "idea_fallback",
        "date": "2026-09-11",
        "window": "1.day",
        "total_diffstat": 0,
        "files_touched": [],
        "commit_messages": [],
        "per_repo": [
            {"name": "ghost-repo", "commit_count": 0, "diffstat": 0, "files_touched": []},
        ],
        "decision_source": "heuristic",
    }
    with patch("collector.resolve_current_branch", return_value=None):
        units = collector.adapt_daily_brief(daily_brief)

    assert len(units) == 1
    assert units[0].integrity_status == "invalid"
    assert units[0].metadata["branch"] is None


# --- M4: commit_messages/mode/source_type carried into metadata ----------
# daily_brief's commit_messages is a flat, cross-repo list (not per-repo
# attributed — daily_brief.py's own compute_metrics() already collapses
# it that way before Collector ever writes the file) — every unit from
# the same daily_brief shares the identical commit_messages list, by
# construction, not an error or a duplication bug.


def test_adapt_daily_brief_carries_commit_messages_and_mode_into_metadata():
    daily_brief = {
        "mode": "fact",
        "date": "2026-09-11",
        "window": "1.day",
        "total_diffstat": 10,
        "files_touched": ["a.py"],
        "commit_messages": ["fix: bug in the daily brief scanner", "chore: bump deps"],
        "per_repo": [
            {"name": "article-pipeline", "commit_count": 2, "diffstat": 10, "files_touched": ["a.py"]},
        ],
        "decision_source": "heuristic",
    }
    with patch("collector.resolve_current_branch", return_value="main"), patch(
        "collector.check_integrity", return_value=("valid", "mocked")
    ):
        units = collector.adapt_daily_brief(daily_brief)

    assert units[0].metadata["commit_messages"] == [
        "fix: bug in the daily brief scanner",
        "chore: bump deps",
    ]
    assert units[0].metadata["mode"] == "fact"
    assert units[0].metadata["source_type"] == "collector_daily_brief"


def test_adapt_manifest_carries_source_type_into_metadata():
    manifest = {
        "scan_timestamp": "2026-09-12T00:50:24.808627+00:00",
        "window_days": 7,
        "repos": [
            {"name": "article-pipeline", "branch": "main", "commit_count": 6, "counts": {"value": 2}},
        ],
    }
    with patch("collector.check_integrity", return_value=("valid", "mocked")):
        units = collector.adapt_manifest(manifest)

    assert units[0].metadata["source_type"] == "collector_manifest"
    assert "commit_messages" not in units[0].metadata
