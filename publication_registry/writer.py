"""Publication Registry — content_id minting + Immutable Lineage output
writer (SPEC.md Data Model, Milestone M1).

Writes one JSON file per publication event to `output/`. A content_id
collision does not automatically mean "different event" or
automatically mean "safe retry" — write_record() reconciles the
incoming record against whatever is already on disk before deciding
what a collision means (see its own docstring for the five outcomes).

**Identity model — investigated, not assumed (see this project's task
history for the full investigation).** This repo has no existing,
established concept of "the same publication event" independent of
content_id — checked directly: author/authoring_context.py,
linkedin_verdict_reader.py, and habr_verdict_to_story.py relate a
claim_id to generated content pre-publish only, none track publish
*attempts*; strategy_layer/write_verdict.py's own Immutable Lineage
guard is a bare run_id existence check with zero field-content
comparison, no precedent for reconciling two records claiming the same
identity; SPEC.md's M2/M3/M7 text never states what makes one
publication attempt a repeat of another. This is a stated assumption
for this chat to revisit once M2 exists and real caller behavior can
be checked against it, not a settled fact:

- **Identity = (`claim_id`, `platform`)** — "which piece, on which
  channel." `url` is deliberately excluded from identity, not included
  (an earlier, retracted version of this task used
  platform+claim_id+url): `url` has no defined value for a blocked
  publication (SPEC.md Functional Requirement #9 writes a Registry
  record on a bootstrap-gate block even though nothing was actually
  posted, so no real per-attempt-unique URL necessarily exists for
  that record) — using it as an identity component risked silently
  treating two genuinely different blocked attempts of the same claim
  as "the same event" purely because they share whatever placeholder
  `url` value a caller happens to use, which is exactly the kind of
  unreviewed assumption this correction exists to catch.
- `claim_id` alone was rejected once already (SPEC.md Functional
  Requirement #3): "the same Claim could in principle be published
  more than once," which is precisely why `content_id`, not
  `claim_id`, is the Registry's primary key. `platform` narrows this:
  two records only share identity here if they're minted with an
  identical claim_id AND platform AND (separately, see below)
  happen to collide on content_id — an already-rare combination this
  model treats conservatively (flag, don't silently merge) rather than
  by inventing a stronger uniqueness guarantee not established
  anywhere in this repo.
- Once identity is established, `url`, `gate_policy`, `gate_version`,
  `gate_status`, and `block_reason` are the fixed-per-event fields
  checked for full agreement (SPEC.md's Test Plan explicitly singles
  out `gate_status` as a case that must never silently succeed under
  disagreement). `published_at`/`gate_evaluated_at` are the only fields
  excluded from every comparison in this module — they may legitimately
  differ across calls regardless of which outcome applies.

content_id minting itself is unchanged from M1 and reuses this
project's existing convention: a UTC timestamp, `%Y%m%dT%H%M%S` — the
same scheme already used for `run_id` throughout strategy_layer/ and
for Claim IDs in claim_extraction/. No UUID4/ULID/suffix/sequence
scheme was introduced.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from pydantic import ValidationError

from contract import PublicationRecord

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

_IDENTITY_FIELDS = ("claim_id", "platform")
_AGREEMENT_FIELDS = ("url", "gate_policy", "gate_version", "gate_status", "block_reason")


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


def mint_content_id(now: datetime | None = None) -> str:
    """Mints a new content_id — UTC timestamp, matching this project's
    run_id/Claim-ID convention (see module docstring). `now` is
    injectable for deterministic tests; production callers omit it.
    """
    moment = now or datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S")


def write_record(record: PublicationRecord) -> str:
    """Writes {content_id}.json (Immutable Lineage) — reconciling
    against whatever already exists at that path rather than assuming
    every collision is either "safe retry" or "unrelated bug".

    Five outcomes:
    1. No existing file -> write, return the new path (unchanged from
       the original M1 behavior).
    2. Existing file unreadable (invalid JSON, or valid JSON that
       doesn't parse as a PublicationRecord) -> PublicationRegistryConflictError.
       Identity can't be verified without reading it; never overwritten.
    3. Existing file readable, same identity (_IDENTITY_FIELDS), and
       every _AGREEMENT_FIELDS value agrees -> idempotent success;
       returns the *existing* file's path, writes nothing.
    4. Same identity, but an _AGREEMENT_FIELDS value disagrees (most
       importantly gate_status/block_reason) -> a real state conflict,
       not a retry -> PublicationRegistryConflictError. Never overwritten.
    5. Different identity (a content_id collision between two logically
       different events) -> PublicationRegistryConflictError. Never
       overwritten.

    published_at/gate_evaluated_at are never part of any comparison —
    they may legitimately differ across calls regardless of outcome.
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
            f"valid PublicationRecord — cannot verify identity against "
            f"the incoming record. Not overwritten."
        ) from exc

    if any(getattr(existing, field) != getattr(record, field) for field in _IDENTITY_FIELDS):
        raise PublicationRegistryConflictError(
            f"{record_path} already exists for content_id={record.content_id!r} "
            f"but describes a different publication event — identity "
            f"fields {_IDENTITY_FIELDS} disagree (content_id collision "
            f"between two logically different events). Not overwritten."
        )

    disagreements = [
        field for field in _AGREEMENT_FIELDS
        if getattr(existing, field) != getattr(record, field)
    ]
    if disagreements:
        raise PublicationRegistryConflictError(
            f"{record_path} already exists for the same publication event "
            f"(content_id={record.content_id!r}, identity {_IDENTITY_FIELDS}) "
            f"but disagrees on {disagreements} — this is a state conflict, "
            f"not a retry. Not overwritten."
        )

    return record_path
