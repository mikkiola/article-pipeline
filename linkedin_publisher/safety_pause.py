"""SAFETY_PAUSE circuit-breaker state — check only, no trigger
(SPEC.md Functional Requirements #10-11, Milestone M2;
docs/adr/0054-m2-ships-core-linkedin-publishing-without-safety-pause-
trigger-or-proactive-credential-alerting.md).

SPEC.md's own text never names concrete state values for `SAFETY_PAUSE`
(it only describes the circuit as "active"/opened/lifted in prose) —
no repo precedent exists for this either (grepped for an existing
circuit-breaker naming convention before writing this: none found).
CLOSED/OPEN is the standard circuit-breaker-pattern vocabulary
(normal-flow / tripped), used here as the least surprising choice
given no project-specific precedent to follow instead.

This module intentionally has no function that ever writes `OPEN` to
the state file — SPEC.md Functional Requirement #10's trigger is "one
explicit `trash` Owner Verdict," which is M3's scope (Owner Verdict
doesn't exist yet). What's built here is only the read side: the
scheduled job's own preflight check, which today always observes
CLOSED (no file present) and will correctly observe OPEN once M3
exists and writes one — that write path is out of this task's scope by
design, not an oversight.
"""

from __future__ import annotations

import json
import os
from enum import Enum

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
STATE_FILE = os.path.join(STATE_DIR, "safety_pause_state.json")


class SafetyPauseState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"


def check_safety_pause_state() -> SafetyPauseState:
    """Returns the current SAFETY_PAUSE state.

    No state file present -> CLOSED (the default, correct state until
    M3's Owner Verdict ever opens the circuit). A present file is read
    and its `state` field returned — this module doesn't validate who
    wrote it or when, since nothing in this task's scope ever writes
    one; a malformed file is a genuine unexpected condition and is
    allowed to raise rather than silently defaulting to CLOSED (a
    corrupt state file failing open would defeat the whole point of a
    safety circuit).
    """
    if not os.path.exists(STATE_FILE):
        return SafetyPauseState.CLOSED

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return SafetyPauseState(data["state"])
