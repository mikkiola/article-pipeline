"""Publication Registry — record schema (SPEC.md Data Model, Milestone
M1).

One record per publication event (SPEC.md Functional Requirement #1),
keyed by `content_id` — the Registry's own minted primary key, never
`claim_id` (Functional Requirement #3: the same Claim could in
principle be published more than once, so `claim_id` cannot be the
primary key). `block_reason` is the one conditional field: required
when `gate_status="block"`, forbidden otherwise (Functional Requirement
#5) — enforced here, at construction time, the same pattern
strategy_layer/contract.py's CanonicalUnit already establishes in this
project for a conditional-field record.

`gate_version` is typed as a plain str — SPEC.md's Data Model doesn't
constrain its format, and this project's own precedent for a version
field (Change Proposal's `prompt_version`/`target_prompt_version`,
SPEC.md Functional Requirement #31) is also untyped free text, not a
strict integer counter. A plain decision, not an open question back to
the task owner.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class PublicationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content_id: str
    platform: Literal["linkedin", "habr"]
    url: str
    published_at: datetime
    claim_id: str

    gate_policy: Literal["bootstrap", "R6"]
    gate_version: str
    gate_status: Literal["pass", "block"]
    block_reason: str | None = None
    gate_evaluated_at: datetime

    @model_validator(mode="after")
    def _check_block_reason_consistency(self) -> "PublicationRecord":
        if self.gate_status == "block":
            if not self.block_reason:
                raise ValueError(
                    "block_reason is required when gate_status='block'"
                )
        else:
            if self.block_reason is not None:
                raise ValueError(
                    "block_reason must be null when gate_status != 'block'"
                )
        return self
