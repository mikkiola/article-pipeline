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
        daily_publish.daily_linkedin_author, "validate_structured_response", lambda response, mode: None
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
