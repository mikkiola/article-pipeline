"""Habr Edit Capture — record schema (SPEC.md Data Model, Milestone M4;
ADR-0050 point 4; docs/adr/0060-habr-edit-capture-as-its-own-component.md).

A new, minimal component — deliberately not an extension of `verdict/`
or `evidence_package/`. Confirmed in a prior read-only architecture
pass, re-stated here since it's load-bearing for this schema's own
field choices:

- `evidence_package/`'s domain is Claim-verification search results
  (`evidence_id`/`claim_id`/`search_query`/`source_url`) — an unrelated
  pipeline stage. Reusing it would couple two unrelated domains on the
  shared English word "evidence" alone.
- `verdict/`'s `VerdictRecord` is keyed by `content_id` and carries a
  closed `verdict_type: Literal["good", "trash", "style-off"]`. Neither
  fits here: FR17/FR20 mean no Habr publish event, and therefore no
  `content_id`, exists anywhere in M4's own scope (the owner publishes
  to Habr herself, outside this pipeline's write path); and a text diff
  has no natural slot in a three-value closed literal.

Two distinct keys, not one (do not conflate them):
- **Domain key** — `folder_id` + `date_stem`: identifies *which
  article* this capture belongs to, per FR18's own
  `YYYY-MM-DD-draft`/`YYYY-MM-DD-final` per-folder convention. Human-
  facing; what a future reader checks to find "the capture for this
  article."
- **Dedup key** — `final_modified_time`, checked within one
  (`folder_id`, `date_stem`) directory before writing: identifies
  *which specific state* of the `-final` file has already been
  captured, so a second scheduled-job run against an untouched file is
  a no-op, while a real re-edit (same filename, new content, a new
  Drive `modifiedTime`) is correctly treated as a new event. Not
  `headRevisionId`: confirmed against the Drive API v3 Files reference
  that `headRevisionId` is "currently only available for files with
  binary content in Google Drive" — the owner's folders hold native
  Google Docs, not binary uploads, so `modifiedTime` is the field
  actually available here, not a fallback.

`has_changes` is an explicit field, not inferred from `diff == ""` by
every future reader. A zero-diff capture (the owner published the
draft unedited) is still written, not skipped — extending this
project's own established "never silently omit state" pattern
(`VerdictRecord.verdict_type`'s `"good"` value is itself a real,
written positive outcome, not an absence; SPEC.md Functional
Requirement 26 states Weekly's `verdict_status` is "never silently
omitted"). Silently skipping an unedited draft would bias Weekly's
future pattern detection toward only ever seeing edited cases.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HabrEditCaptureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    folder_id: str
    folder_name: str | None = None
    date_stem: str

    draft_file_id: str
    final_file_id: str
    final_modified_time: datetime

    diff: str
    has_changes: bool

    captured_at: datetime
