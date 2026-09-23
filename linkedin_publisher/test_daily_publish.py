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

import sys
from datetime import datetime, timezone
from pathlib import Path

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
