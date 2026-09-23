"""Publication Registry — content_id minting + Immutable Lineage output
writer (SPEC.md Data Model, Milestone M1).

Writes one JSON file per publication event to `output/`, matching this
project's established Immutable Lineage convention
(strategy_layer/write_verdict.py; evidence_package's now-deleted
write_evidence.py followed the same rule): never overwrites an existing
record — a `content_id` collision raises FileExistsError instead of
silently overwriting.

`content_id` minting reuses this project's existing convention, not a
new one: a UTC timestamp, `%Y%m%dT%H%M%S` — the same scheme already
used for `run_id` throughout strategy_layer/ (run_pilot.py,
run_collector_pilot.py, run_linkedin_pilot.py, run_habr_pilot.py) and
for Claim IDs in claim_extraction/. No UUID4/ULID was introduced; this
stays consistent with the repo-wide precedent rather than adding a
second ID format to the project. Collision safety doesn't depend on
timestamp uniqueness alone — write_record()'s FileExistsError guard
below is the actual Immutable Lineage enforcement, same as every other
writer in this project.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from contract import PublicationRecord

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def mint_content_id(now: datetime | None = None) -> str:
    """Mints a new content_id — UTC timestamp, matching this project's
    run_id/Claim-ID convention (see module docstring). `now` is
    injectable for deterministic tests; production callers omit it.
    """
    moment = now or datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S")


def write_record(record: PublicationRecord) -> str:
    """Writes {content_id}.json (Immutable Lineage).

    Never overwrites an existing record: a content_id collision raises
    FileExistsError instead of silently overwriting — same pattern as
    strategy_layer/write_verdict.py's write_outputs().
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    record_path = os.path.join(OUTPUT_DIR, f"{record.content_id}.json")

    if os.path.exists(record_path):
        raise FileExistsError(
            f"{record_path} already exists — Immutable Lineage forbids "
            f"overwriting a previous publication record."
        )

    with open(record_path, "w", encoding="utf-8") as f:
        f.write(record.model_dump_json(indent=2))

    return record_path
