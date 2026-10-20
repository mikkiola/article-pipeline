#!/usr/bin/env python3
"""Telegram notification, sent only AFTER the artifacts are committed and
pushed (SPEC.md M9; owner decision 2026-10-15).

The message carries the run outcome and a stable reference to the committed
artifacts (registry-data commit SHA + path), never the draft text. Delivery is
logged, never written into the immutable run record. A notification problem
never fails the workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


def build_message(record: dict, reference: str) -> str:
    lines = [
        f"Habr draft run {record.get('run_id')}",
        f"outcome: {record.get('observable_outcome')}",
    ]
    if record.get("mode") == "calibration":
        lines.append("mode: calibration (acceptance not evaluated)")
    if record.get("failure_kind"):
        lines.append(f"failure_kind: {record['failure_kind']}")
    if record.get("reason"):
        lines.append(f"reason: {record['reason']}")
    lines.append("not publication approval")
    lines.append(f"artifacts: {reference}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Notify the owner about a committed Habr draft run.")
    parser.add_argument("--run-record", required=True)
    parser.add_argument("--reference", required=True,
                        help="Stable reference to the committed artifacts")
    args = parser.parse_args()

    record = json.loads(Path(args.run_record).read_text(encoding="utf-8"))
    message = build_message(record, args.reference)
    if not (os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")):
        print("notification not configured (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID unset); not sent")
        return
    try:
        from habr_edit_capture import telegram_send

        telegram_send.send_habr_draft(message)
        print("notification sent")
    except Exception as error:  # noqa: BLE001 - delivery is logged, never fatal
        print(f"notification failed: {type(error).__name__}")


if __name__ == "__main__":
    main()
