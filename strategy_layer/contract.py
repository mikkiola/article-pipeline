"""Strategy Layer — canonical Anti-Corruption-Layer input contract
(SPEC.md Data Model, Milestone M1).

CanonicalUnit is the one shape every source adapter must produce
before Strategy Layer's core logic (pre_filter.py, framing.py,
write_verdict.py) ever sees a record — no adapter-specific field name
is read past this boundary. Two independent verification dimensions
(the two-dimension model, ADR to be filed per SPEC.md's Migration
Sequence step 6) replace the old single verified/disputed/unverifiable
/pending status:

- integrity_status: every unit, every source, no exceptions — is this
  record authentic/provenanced?
- corroboration_status: only units making a falsifiable assertion.
  not_applicable is a first-class value for bare records (e.g.
  Collector's raw telemetry).

Validation happens here, at construction time — extra="forbid" plus
the model_validator below IS the input-validation gate that used to
live in pre_filter.py's join_claims_and_evidence() (removed, M2). An
adapter that cannot produce a complete, valid CanonicalUnit from a raw
record raises before Strategy Layer ever sees it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class CanonicalUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str
    source: Literal["brain", "collector"]
    created_at: datetime

    integrity_status: Literal["valid", "invalid"]
    integrity_check_method: str

    corroboration_status: Literal[
        "corroborated", "disputed", "unsubstantiated", "pending", "not_applicable"
    ]
    assertion_text: str | None = None

    source_url: str | None = None
    license: str | None = None

    metadata: dict[str, Any] = {}

    @model_validator(mode="after")
    def _check_assertion_and_corroboration_consistency(self) -> "CanonicalUnit":
        if self.corroboration_status == "not_applicable":
            if self.assertion_text is not None:
                raise ValueError(
                    "assertion_text must be null when corroboration_status "
                    "is not_applicable"
                )
        else:
            if not self.assertion_text:
                raise ValueError(
                    f"assertion_text is required when corroboration_status="
                    f"{self.corroboration_status!r}"
                )

        if self.corroboration_status == "corroborated":
            if not self.source_url or not self.license:
                raise ValueError(
                    "source_url and license are required when "
                    "corroboration_status=corroborated (R8)"
                )

        return self
