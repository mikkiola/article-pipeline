"""Owner Verdict — record schema (SPEC.md Data Model, Milestone M3).

One record per Owner Verdict event (SPEC.md Functional Requirements
14-16), keyed by `content_id` — never `claim_id`, the same primary-key
discipline publication_registry/contract.py already establishes in
this project (ADR-0053's reasoning applies here too: the same Claim
could in principle be published, and separately verdicted, more than
once).

Unlike Publication Registry's one-record-per-content_id model, Owner
Verdict is explicitly an append-only event stream (ADR-0050 point 1,
confirmed current and unchanged by ADR-0052; SPEC.md Functional
Requirement 14): more than one verdict record may exist for the same
content_id over time. writer.py reflects this directly — see its own
module docstring.

Always "Owner Verdict" in prose, never bare "verdict" (SPEC.md's own
Glossary) — this repo already has an unrelated, pre-existing "Strategy
Verdict" concept (strategy_layer/write_verdict.py,
strategy_layer/output/verdict_*.json) that this package must not be
confused with, by name or by file-path pattern.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class VerdictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    verdict_type: Literal["good", "trash", "style-off"]
    received_at: datetime
    comment: str | None = None
