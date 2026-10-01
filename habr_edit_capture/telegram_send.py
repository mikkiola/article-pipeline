"""Habr draft hand-off — Telegram `sendMessage` only (SPEC.md Functional
Requirement 17; SPEC.md API Design, "Telegram Bot API, M4").

Standalone one-way send — no dependency on `[B-065]`'s shared
send/receive transport (confirmed in a prior session's canon fix,
commit `aa14bb9`: FR20 explicitly rules out any round-trip for this
milestone, so there is nothing here for a receive-side transport to
do). Deliberately NOT built on top of `[B-065]` preemptively: that
item is still unbuilt (confirmed: `mikkiola/tooltempest` has zero
Telegram-named files, checked directly in a prior session), and
building against an unbuilt dependency for a requirement that doesn't
need it would be exactly the "needless pre-coupling" this project's
own `/spec` discipline avoids.

`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` env-var convention and the
`_call()` isolation pattern are copied from the real, already-running
precedent (`mikkiola/analyzer/scripts/telegram_bot.py`'s
`send_message()`), read directly this session — not reinvented. Only
`send_message` is implemented here; `get_updates` is M5's own,
separate, not-yet-built scope (FR20), and would need `[B-065]` once
M5 actually builds it.

**Not wired into `author/` by this task.** See this task's own report,
Part 5: `author/habr_weekly_author.py`/`habr_verdict_to_story.py` are
pure rendering/business-logic functions with no file-writing or CLI
entry point, and the only script that calls them end-to-end
(`strategy_layer/run_habr_pilot.py`) is explicitly self-described as
"Throwaway orchestration... not TDD'd for that reason," with a
hardcoded, stale manifest path, and is not invoked by any
`.github/workflows/` schedule. There is no real production trigger
point to wire a Telegram send into without first building one — doing
so here would decorate a one-off manual pilot script, not "properly
trigger" anything, which this task's own instructions name as a reason
to stop and report rather than force a minimal patch.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

_API_URL = "https://api.telegram.org/bot{token}/{method}"


def _call(method: str, params: dict, token: str | None = None) -> dict:
    """Isolated so tests can monkeypatch this single function rather
    than mocking urllib directly — same isolation point
    `analyzer/scripts/telegram_bot.py`'s own `_call()` uses, for the
    same reason: no real network call in unit tests.
    """
    token = token or TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    url = _API_URL.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def send_habr_draft(text: str, chat_id: str | None = None, token: str | None = None) -> dict:
    """Sends `text` (the Habr draft itself, or a link to it, per FR17)
    to the owner's configured Telegram chat. One call, no round-trip
    (FR20) — the full extent of M4's Telegram involvement.
    """
    chat_id = chat_id or TELEGRAM_CHAT_ID
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set")
    return _call("sendMessage", {"chat_id": chat_id, "text": text}, token=token)
