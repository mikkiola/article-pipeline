"""Publication Registry — Immutable Lineage output writer (SPEC.md Data
Model, Milestone M1).

`content_id` is caller-supplied, never minted or reconstructed here —
see docs/adr/0053-content-id-ownership-moves-to-caller.md for the full
reasoning (supersedes SPEC.md Functional Requirement #3's "the
Registry's own minted primary key" wording on the minting-location
point specifically; content_id vs. claim_id as the primary key is
unchanged). The writer's job is narrow: persist a new record, or
reconcile an incoming one against whatever already exists at that
content_id's path.

write_record() has four outcomes:
1. No existing file -> create it, return the new path.
2. Existing file unreadable (invalid JSON, or valid JSON that doesn't
   parse as a PublicationRecord) -> PublicationRegistryConflictError.
   Never overwritten.
3. Existing file readable and agrees with the incoming record on every
   field except `published_at`/`gate_evaluated_at` (which may
   legitimately differ across calls describing the same event, e.g. a
   retry that regenerates timestamps) -> idempotent success; returns
   the *existing* file's path, writes nothing.
4. Existing file readable but disagrees on any other field ->
   PublicationRegistryConflictError. Never overwritten.

Since content_id is now the caller's own stable identity for one
logical publication event (ADR-0053), any disagreement once content_id
already matches is simply a conflict — there is no separate identity-
vs-agreement-field distinction to make inside the writer anymore.
"""

from __future__ import annotations

import json
import os

from pydantic import ValidationError

from contract import PublicationRecord

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

_COMPARISON_EXCLUDED_FIELDS = ("published_at", "gate_evaluated_at")


class PublicationRegistryConflictError(RuntimeError):
    """Raised by write_record() when an existing on-disk record can't be
    safely reconciled against an incoming one.

    SPEC.md defines SYSTEM_FAILURE only as an M8/Quality-Gate-level
    pipeline-health concept (Linkup down, a verifier crashed, the
    publisher errored) with no local exception class anywhere in this
    repo — quality_gate/ is not started (.gitkeep only), confirmed by
    direct check. This is the registry-write-level stand-in for that
    concept, named per this project's existing <Domain>Error(RuntimeError)
    convention (evidence_package.SearchBackendError,
    evidence_package.SearchBudgetError, author.AuthorLLMError).
    """


def _fields_agree(existing: PublicationRecord, incoming: PublicationRecord) -> bool:
    return all(
        getattr(existing, field) == getattr(incoming, field)
        for field in PublicationRecord.model_fields
        if field not in _COMPARISON_EXCLUDED_FIELDS
    )


def write_record(record: PublicationRecord) -> str:
    """Writes {content_id}.json (Immutable Lineage) — see module
    docstring for the four outcomes.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    record_path = os.path.join(OUTPUT_DIR, f"{record.content_id}.json")

    if not os.path.exists(record_path):
        with open(record_path, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))
        return record_path

    with open(record_path, "r", encoding="utf-8") as f:
        raw_existing = f.read()

    try:
        existing = PublicationRecord(**json.loads(raw_existing))
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        raise PublicationRegistryConflictError(
            f"{record_path} already exists but could not be read as a "
            f"valid PublicationRecord — cannot verify agreement with "
            f"the incoming record. Not overwritten."
        ) from exc

    if _fields_agree(existing, record):
        return record_path

    disagreements = [
        field
        for field in PublicationRecord.model_fields
        if field not in _COMPARISON_EXCLUDED_FIELDS
        and getattr(existing, field) != getattr(record, field)
    ]
    raise PublicationRegistryConflictError(
        f"{record_path} already exists for content_id={record.content_id!r} "
        f"but disagrees on {disagreements} — this is a state conflict, "
        f"not a retry. Not overwritten."
    )
