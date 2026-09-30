"""Owner Verdict — Immutable Lineage output writer (SPEC.md Data Model,
Milestone M3).

Owner Verdict is an append-only event stream (ADR-0050 point 1,
confirmed current and unchanged by ADR-0052; SPEC.md Functional
Requirement 14) — unlike publication_registry.writer.write_record(),
which reconciles a single record per content_id, write_verdict() below
never checks for or rejects an existing record: every call appends a
new, distinct record file. No lifecycle coupling (Functional
Requirement 16) — a content_id with zero verdict records is a complete,
valid state, not an error; read_verdicts() returns an empty list for
one, never raises.

Naming: `verdict/output/<content_id>/<record_id>.json`, one file per
verdict event, `record_id` a fresh uuid4 hex string per call.
Deliberately NOT a `verdict_*.json` flat pattern —
strategy_layer/output/ already uses exactly that pattern for an
unrelated concept ("Strategy Verdict," SPEC.md's own Glossary); nesting
under a per-content_id directory, with uuid4-named files, means no grep
or script could ever conflate the two on path or filename alone.

No registry-data-style branch separation (contrast
docs/adr/0055-publication-registry-state-lives-on-registry-data-
branch.md): that separation exists specifically because a scheduled
GitHub Actions workflow writes Publication Registry records and `main`
only accepts PRs. M3, as scoped by CURRENT_MISSION.md, has no
scheduled-workflow write path yet — verdicts are recorded via a direct,
manual/test-only interface for this milestone; Telegram delivery is
M5's separate, not-yet-built scope. `verdict/output/` therefore lives
in `main`'s own working tree, the same as strategy_layer/output/, until
M5 actually introduces an automated write path that would need branch
separation — decided here, not copied from Registry's pattern
reflexively.
"""

from __future__ import annotations

import json
import os
import uuid

from contract import VerdictRecord

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def write_verdict(record: VerdictRecord) -> str:
    """Appends `record` as a new file under
    `verdict/output/<content_id>/<record_id>.json`. Always creates a new
    file — never reconciles against or overwrites an existing one, since
    more than one verdict event per content_id is expected (an
    append-only stream, not a one-record-per-key registry).
    """
    content_dir = os.path.join(OUTPUT_DIR, record.content_id)
    os.makedirs(content_dir, exist_ok=True)

    record_id = uuid.uuid4().hex
    record_path = os.path.join(content_dir, f"{record_id}.json")

    if os.path.exists(record_path):
        raise FileExistsError(
            f"{record_path} already exists — a fresh uuid4 collided, "
            f"which should not happen; not overwritten."
        )

    with open(record_path, "w", encoding="utf-8") as f:
        f.write(record.model_dump_json(indent=2))

    return record_path


def read_verdicts(content_id: str) -> list[VerdictRecord]:
    """Returns every verdict record for `content_id`, ordered by
    `received_at` ascending. Returns an empty list (not None, never
    raises) when `content_id` has zero verdict records — SPEC.md's
    `missing` verdict_status case (Functional Requirement 16, M6): a
    content_id with no verdicts is a complete, valid, un-verdicted
    publication, not an error or an absent lookup.
    """
    content_dir = os.path.join(OUTPUT_DIR, content_id)
    if not os.path.isdir(content_dir):
        return []

    records = []
    for filename in os.listdir(content_dir):
        if not filename.endswith(".json"):
            continue
        record_path = os.path.join(content_dir, filename)
        with open(record_path, "r", encoding="utf-8") as f:
            raw = f.read()
        records.append(VerdictRecord(**json.loads(raw)))

    return sorted(records, key=lambda r: r.received_at)
