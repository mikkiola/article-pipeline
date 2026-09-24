"""Tests for linkedin_publisher/linkedin_client.py.

No real LinkedIn API call is ever made — every test mocks `requests.post`
or works purely against environment variables. check_token_preflight()'s
fail-closed branches are exactly the class of mechanism
docs/CONSTITUTION.md's TDD rule targets (a gate whose entire job is
triggering correctly under specific conditions).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import linkedin_client  # noqa: E402


# --- check_token_preflight -------------------------------------------


def test_preflight_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="LINKEDIN_ACCESS_TOKEN is not set"):
        linkedin_client.check_token_preflight()


def test_preflight_raises_when_expiry_missing(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", raising=False)
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="EXPIRES_AT is not set"):
        linkedin_client.check_token_preflight()


def test_preflight_raises_when_expiry_unparseable(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "not-a-date")
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="not a parseable ISO 8601"):
        linkedin_client.check_token_preflight()


def test_preflight_raises_when_token_expired(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "2026-09-01T00:00:00+00:00")
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="expired"):
        linkedin_client.check_token_preflight(now=now)


def test_preflight_raises_when_token_expires_exactly_now(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "2026-09-24T00:00:00+00:00")
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="expired"):
        linkedin_client.check_token_preflight(now=now)


def test_preflight_passes_when_token_present_and_not_expired(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "2026-11-01T00:00:00+00:00")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:ABC123")
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    linkedin_client.check_token_preflight(now=now)  # must not raise


def test_preflight_treats_naive_expiry_as_utc(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "2026-11-01T00:00:00")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:ABC123")
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    linkedin_client.check_token_preflight(now=now)  # must not raise


# --- LINKEDIN_PERSON_URN format validation ------------------------------


def test_person_urn_accepts_valid_value(monkeypatch):
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:AbC_123-x")
    assert linkedin_client._person_urn() == "urn:li:person:AbC_123-x"


def test_person_urn_rejects_empty(monkeypatch):
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "")
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="LINKEDIN_PERSON_URN is not set"):
        linkedin_client._person_urn()


@pytest.mark.parametrize(
    "bad_urn",
    [
        "{urn:li:person:abc}",  # curly braces — the real production failure
        " urn:li:person:abc",  # leading whitespace
        "urn:li:person:abc ",  # trailing whitespace
        "urn:li:person:abc\n",  # trailing newline (would slip past a bare `$`)
        "urn:li:organization:123",  # wrong entity type
        "urn:li:person:",  # no id
    ],
)
def test_person_urn_rejects_malformed_value(monkeypatch, bad_urn):
    monkeypatch.setenv("LINKEDIN_PERSON_URN", bad_urn)
    with pytest.raises(linkedin_client.LinkedInPublisherError) as excinfo:
        linkedin_client._person_urn()
    message = str(excinfo.value)
    assert repr(bad_urn) in message
    assert "urn:li:person:<id>" in message


def test_preflight_raises_on_malformed_person_urn_before_any_network_call(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "2026-11-01T00:00:00+00:00")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "{urn:li:person:abc}")
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    with mock.patch.object(linkedin_client.requests, "post") as mock_post:
        with pytest.raises(linkedin_client.LinkedInPublisherError, match="malformed"):
            linkedin_client.check_token_preflight(now=now)
    mock_post.assert_not_called()


def test_preflight_raises_when_person_urn_missing(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "2026-11-01T00:00:00+00:00")
    monkeypatch.delenv("LINKEDIN_PERSON_URN", raising=False)
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="LINKEDIN_PERSON_URN is not set"):
        linkedin_client.check_token_preflight(now=now)


# --- publish_post -------------------------------------------------------


def _fake_response(status_code: int, headers: dict, text: str = ""):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.headers = headers
    resp.text = text
    return resp


def test_publish_post_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="LINKEDIN_ACCESS_TOKEN is not set"):
        linkedin_client.publish_post("hello")


def test_publish_post_raises_when_person_urn_missing(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.delenv("LINKEDIN_PERSON_URN", raising=False)
    with pytest.raises(linkedin_client.LinkedInPublisherError, match="LINKEDIN_PERSON_URN is not set"):
        linkedin_client.publish_post("hello")


def test_publish_post_returns_url_on_success(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:ABC123")

    fake_resp = _fake_response(201, {"x-restli-id": "urn:li:share:999"})
    with mock.patch.object(linkedin_client.requests, "post", return_value=fake_resp) as mock_post:
        url = linkedin_client.publish_post("hello world")

    assert url == "https://www.linkedin.com/feed/update/urn:li:share:999/"
    called_kwargs = mock_post.call_args.kwargs
    assert called_kwargs["json"]["commentary"] == "hello world"
    assert called_kwargs["json"]["author"] == "urn:li:person:ABC123"
    assert called_kwargs["headers"]["Authorization"] == "Bearer fake-token"


def test_publish_post_raises_on_non_201_status(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:ABC123")

    fake_resp = _fake_response(401, {}, text="unauthorized")
    with mock.patch.object(linkedin_client.requests, "post", return_value=fake_resp):
        with pytest.raises(linkedin_client.LinkedInPublisherError, match="401"):
            linkedin_client.publish_post("hello world")


def test_publish_post_error_message_includes_response_headers(monkeypatch):
    # Regression test: a real production 403 had an empty JSON body
    # ({"message":"","status":403}) with no diagnostic detail —
    # response headers are the only remaining place LinkedIn might put
    # an explanation for an empty-body error, so they must appear in
    # the raised error, not just response.text.
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:ABC123")

    fake_resp = _fake_response(
        403, {"x-restli-error-message": "insufficient scope"}, text='{"message":"","status":403}'
    )
    with mock.patch.object(linkedin_client.requests, "post", return_value=fake_resp):
        with pytest.raises(linkedin_client.LinkedInPublisherError, match="insufficient scope"):
            linkedin_client.publish_post("hello world")


def test_publish_post_raises_when_201_but_no_id_header(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("LINKEDIN_PERSON_URN", "urn:li:person:ABC123")

    fake_resp = _fake_response(201, {})
    with mock.patch.object(linkedin_client.requests, "post", return_value=fake_resp):
        with pytest.raises(linkedin_client.LinkedInPublisherError, match="no x-restli-id header"):
            linkedin_client.publish_post("hello world")
