"""Habr Edit Capture — Immutable Lineage output writer (SPEC.md Data
Model, Milestone M4; ADR-0050 point 4).

Append-only, per-article event stream — same shape of design as
`verdict/writer.py`'s `write_verdict()`, not `publication_registry/
writer.py`'s single-record-per-key reconciliation: more than one real
edit-capture event is expected per article (a re-edit is a new event,
not a correction of the first one), matching ADR-0050 point 4's framing
of a Habr edit as "the same kind of signal" a verdict is — an async,
accumulating stream, not a reconciled registry entry.

Idempotency (contract.py's "dedup key" vs "domain key" distinction):
`write_capture()` lists whatever records already exist for the
incoming record's (`folder_id`, `date_stem`) domain key and compares
each one's `final_modified_time` against the incoming record's. An
exact match means this precise state of the `-final` file was already
captured — written by the same or a prior scheduled-job run — and
`write_capture()` returns `None`, writing nothing. No match (first
capture for this article, or a genuine re-edit with a new
`modifiedTime`) appends a new record.

Branch separation (same reasoning as ADR-0055, applied by analogy, not
copied blindly): this component's own scheduled job
(`.github/workflows/habr-edit-capture.yml`) writes records the same
way `linkedin-daily-publish.yml` writes Publication Registry records —
`main` is branch-protected (ADR-0055's own Context), and a scheduled
workflow's bot identity has no admin bypass (ADR-0039), so its output
cannot live on `main` either. `HABR_EDIT_CAPTURE_OUTPUT_DIR` (when set
and non-empty) points this writer at a directory outside this
checkout, read once at import time — same pattern, same env-var-naming
convention, as `publication_registry/writer.py`'s own
`REGISTRY_OUTPUT_DIR`.
"""

from __future__ import annotations

import json
import os
import uuid

from contract import HabrEditCaptureRecord

OUTPUT_DIR = os.environ.get("HABR_EDIT_CAPTURE_OUTPUT_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "output"
)


def _article_dir(folder_id: str, date_stem: str) -> str:
    return os.path.join(OUTPUT_DIR, folder_id, date_stem)


def write_capture(record: HabrEditCaptureRecord) -> str | None:
    """Appends `record` as a new file under
    `habr_edit_capture/output/<folder_id>/<date_stem>/<record_id>.json`,
    unless a record already exists for this exact
    (folder_id, date_stem, final_modified_time) combination, in which
    case nothing is written and None is returned (idempotent no-op, not
    an error — a repeated scheduled-job run against an unchanged
    `-final` file must not produce a duplicate).
    """
    for existing in read_captures(record.folder_id, record.date_stem):
        if existing.final_modified_time == record.final_modified_time:
            return None

    article_dir = _article_dir(record.folder_id, record.date_stem)
    os.makedirs(article_dir, exist_ok=True)

    record_id = uuid.uuid4().hex
    record_path = os.path.join(article_dir, f"{record_id}.json")

    if os.path.exists(record_path):
        raise FileExistsError(
            f"{record_path} already exists — a fresh uuid4 collided, "
            f"which should not happen; not overwritten."
        )

    with open(record_path, "w", encoding="utf-8") as f:
        f.write(record.model_dump_json(indent=2))

    return record_path


def read_captures(folder_id: str, date_stem: str) -> list[HabrEditCaptureRecord]:
    """Returns every capture record for (folder_id, date_stem), ordered
    by `captured_at` ascending. Returns an empty list (not None, never
    raises) when no capture has happened yet for this article — the
    same "absence is a complete, valid state" discipline
    `verdict/writer.py`'s `read_verdicts()` already establishes.
    """
    article_dir = _article_dir(folder_id, date_stem)
    if not os.path.isdir(article_dir):
        return []

    records = []
    for filename in os.listdir(article_dir):
        if not filename.endswith(".json"):
            continue
        record_path = os.path.join(article_dir, filename)
        with open(record_path, "r", encoding="utf-8") as f:
            raw = f.read()
        records.append(HabrEditCaptureRecord(**json.loads(raw)))

    return sorted(records, key=lambda r: r.captured_at)
