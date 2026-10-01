"""Tests for habr_edit_capture/telegram_send.py. Mocked HTTP throughout
— no real network call, matching analyzer/scripts/telegram_bot.py's own
Test Plan precedent (mocked in unit tests; a real send is a separate,
manual step)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telegram_send  # noqa: E402


def test_send_habr_draft_calls_sendmessage_with_configured_chat_id(monkeypatch):
    captured = {}

    def fake_call(method, params, token=None):
        captured["method"] = method
        captured["params"] = params
        return {"ok": True}

    monkeypatch.setattr(telegram_send, "_call", fake_call)

    telegram_send.send_habr_draft("here is the draft", chat_id="12345", token="fake-token")

    assert captured["method"] == "sendMessage"
    assert captured["params"] == {"chat_id": "12345", "text": "here is the draft"}


def test_send_habr_draft_raises_without_chat_id(monkeypatch):
    monkeypatch.setattr(telegram_send, "TELEGRAM_CHAT_ID", None)
    with pytest.raises(RuntimeError, match="TELEGRAM_CHAT_ID"):
        telegram_send.send_habr_draft("text", token="fake-token")


def test_call_raises_without_token(monkeypatch):
    monkeypatch.setattr(telegram_send, "TELEGRAM_BOT_TOKEN", None)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        telegram_send._call("sendMessage", {"chat_id": "1", "text": "hi"})


def test_send_habr_draft_falls_back_to_env_chat_id(monkeypatch):
    monkeypatch.setattr(telegram_send, "TELEGRAM_CHAT_ID", "env-chat-id")
    captured = {}

    def fake_call(method, params, token=None):
        captured["params"] = params
        return {"ok": True}

    monkeypatch.setattr(telegram_send, "_call", fake_call)

    telegram_send.send_habr_draft("text", token="fake-token")

    assert captured["params"]["chat_id"] == "env-chat-id"
