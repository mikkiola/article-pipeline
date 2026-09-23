"""LinkedIn API client + token preflight (SPEC.md Milestone M2,
docs/adr/0054-m2-ships-core-linkedin-publishing-without-safety-pause-
trigger-or-proactive-credential-alerting.md).

Personal-profile posting via `POST /rest/posts`, per the Share on
LinkedIn / `w_member_social` flow (facts confirmed in
docs/adr/0049-publication-channel-order-linkedin-first.md: self-serve,
no partner review; ~60-day token expiry). This endpoint accepts no
client-supplied idempotency key — this pipeline's own `content_id` +
Publication Registry preflight (`publication_registry.writer.
write_record()`'s existing-file check) is the only idempotency
protection a retry gets; this client makes no attempt to deduplicate on
its own.

Three environment variables, all owner-supplied (manual OAuth/setup,
out of scope for this component — see the ADR's Consequences section):
- LINKEDIN_ACCESS_TOKEN — the bearer token itself.
- LINKEDIN_ACCESS_TOKEN_EXPIRES_AT — ISO 8601 timestamp. Required
  alongside the token: with no expiry information, "not expired" can't
  be confirmed, so the preflight fails closed (see
  check_token_preflight()) rather than assuming a missing value means
  "still valid." This is a real, additional setup requirement this
  task discovered and is flagging here, not something SPEC.md's
  Functional Requirement #13 named explicitly.
- LINKEDIN_PERSON_URN — the full `urn:li:person:{id}` author URN
  LinkedIn's post payload requires. Also not named explicitly anywhere
  in SPEC.md's text; flagged the same way.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

_POSTS_ENDPOINT = "https://api.linkedin.com/rest/posts"
_LINKEDIN_VERSION = "202509"  # LinkedIn's YYYYMM versioned-REST-API header value.
_RESTLI_PROTOCOL_VERSION = "2.0.0"


class LinkedInPublisherError(RuntimeError):
    """Raised for any condition that must block publishing: a missing
    or expired token, a missing person URN, or a failed API call.

    SPEC.md defines SYSTEM_FAILURE only as an M8/Quality-Gate-level
    pipeline-health concept, with no local exception class established
    anywhere in this repo for it (quality_gate/ is not started —
    .gitkeep only, confirmed by direct check).
    publication_registry.writer.PublicationRegistryConflictError is a
    different domain (registry write-reconciliation, not
    credential/API failure) — reusing it here would be a semantic
    mismatch, not a genuine shared mechanism. This is the
    linkedin_publisher-scoped stand-in, named per this project's
    existing <Domain>Error(RuntimeError) convention
    (evidence_package.SearchBackendError, author.AuthorLLMError,
    publication_registry.writer.PublicationRegistryConflictError).
    """


def check_token_preflight(now: datetime | None = None) -> None:
    """Fail-closed preflight (SPEC.md Functional Requirement #13's M2
    answer to token expiry — see the ADR's Decision section for why
    this, and not a proactive alert, is M2's complete scope here).

    Raises LinkedInPublisherError, and never publishes, when:
    - LINKEDIN_ACCESS_TOKEN is unset or empty.
    - LINKEDIN_ACCESS_TOKEN_EXPIRES_AT is unset, empty, or unparseable.
    - The parsed expiry timestamp is not in the future relative to `now`.

    `now` is injectable for deterministic tests; production callers omit it.
    """
    moment = now or datetime.now(timezone.utc)

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise LinkedInPublisherError(
            "LINKEDIN_ACCESS_TOKEN is not set — cannot publish. Not a "
            "SAFETY_PAUSE (no Owner Verdict is involved); this is a "
            "missing-credential failure."
        )

    expires_at_raw = os.environ.get("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT")
    if not expires_at_raw:
        raise LinkedInPublisherError(
            "LINKEDIN_ACCESS_TOKEN_EXPIRES_AT is not set — cannot confirm "
            "the token is unexpired, so the preflight fails closed rather "
            "than assuming it's still valid."
        )

    try:
        expires_at = datetime.fromisoformat(expires_at_raw)
    except ValueError as exc:
        raise LinkedInPublisherError(
            f"LINKEDIN_ACCESS_TOKEN_EXPIRES_AT={expires_at_raw!r} is not a "
            f"parseable ISO 8601 timestamp — failing closed."
        ) from exc

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= moment:
        raise LinkedInPublisherError(
            f"LINKEDIN_ACCESS_TOKEN expired at {expires_at.isoformat()} "
            f"(now: {moment.isoformat()}) — cannot publish."
        )


def _person_urn() -> str:
    urn = os.environ.get("LINKEDIN_PERSON_URN")
    if not urn:
        raise LinkedInPublisherError(
            "LINKEDIN_PERSON_URN is not set — cannot build a post payload "
            "without an author URN."
        )
    return urn


def publish_post(text: str) -> str:
    """Publishes `text` as a personal-profile post via `POST
    /rest/posts`. Returns the published post's URL.

    Callers are expected to have already called check_token_preflight()
    — this function re-reads LINKEDIN_ACCESS_TOKEN itself (not passed
    the token directly) so it can be called in isolation in tests
    without threading the token through every call site, matching this
    project's existing `_get_api_key()`-per-call convention
    (author/daily_linkedin_author.py).
    """
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise LinkedInPublisherError(
            "LINKEDIN_ACCESS_TOKEN is not set — publish_post() called "
            "without a prior successful check_token_preflight()."
        )
    author_urn = _person_urn()

    payload = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": _LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": _RESTLI_PROTOCOL_VERSION,
    }

    response = requests.post(_POSTS_ENDPOINT, json=payload, headers=headers, timeout=30)
    if response.status_code != 201:
        raise LinkedInPublisherError(
            f"LinkedIn API returned {response.status_code}, expected 201: "
            f"{response.text}"
        )

    post_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
    if not post_id:
        raise LinkedInPublisherError(
            f"LinkedIn API returned 201 but no x-restli-id header carrying "
            f"the new post's id: headers={dict(response.headers)!r}"
        )

    return f"https://www.linkedin.com/feed/update/{post_id}/"
