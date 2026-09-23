"""Tests for linkedin_publisher/safety_pause.py.

Only tests the read side (check_safety_pause_state()) — this module
ships no writer, per docs/adr/0054's explicit scope boundary (M3's
Owner Verdict is the only intended trigger, not built yet). The OPEN
case below writes a raw fixture file directly in the test, not through
any production code path — it exists to prove the reader correctly
reports OPEN once M3 eventually writes one, not to exercise a writer
this module doesn't have.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safety_pause  # noqa: E402


def test_no_state_file_means_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(safety_pause, "STATE_FILE", str(tmp_path / "safety_pause_state.json"))
    assert safety_pause.check_safety_pause_state() == safety_pause.SafetyPauseState.CLOSED


def test_state_file_with_closed_reads_closed(tmp_path, monkeypatch):
    state_file = tmp_path / "safety_pause_state.json"
    state_file.write_text(json.dumps({"state": "CLOSED"}), encoding="utf-8")
    monkeypatch.setattr(safety_pause, "STATE_FILE", str(state_file))
    assert safety_pause.check_safety_pause_state() == safety_pause.SafetyPauseState.CLOSED


def test_state_file_with_open_reads_open(tmp_path, monkeypatch):
    # Fixture file written directly by the test, not via any production
    # writer — see module docstring above.
    state_file = tmp_path / "safety_pause_state.json"
    state_file.write_text(json.dumps({"state": "OPEN"}), encoding="utf-8")
    monkeypatch.setattr(safety_pause, "STATE_FILE", str(state_file))
    assert safety_pause.check_safety_pause_state() == safety_pause.SafetyPauseState.OPEN


def test_state_file_with_invalid_value_raises(tmp_path, monkeypatch):
    state_file = tmp_path / "safety_pause_state.json"
    state_file.write_text(json.dumps({"state": "SOMETHING_ELSE"}), encoding="utf-8")
    monkeypatch.setattr(safety_pause, "STATE_FILE", str(state_file))
    with pytest.raises(ValueError):
        safety_pause.check_safety_pause_state()
