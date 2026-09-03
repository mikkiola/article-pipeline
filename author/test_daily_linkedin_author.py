#!/usr/bin/env python3
"""Plain-assert tests for daily_linkedin_author.py.

Run: python3 test_daily_linkedin_author.py

Matches this directory's own test_pipeline.py convention (plain
asserts, no framework). No real API call is ever made — the Anthropic
client is mocked in every test that reaches call_model().
"""

import os
from unittest import mock

import daily_linkedin_author as author_llm

SAMPLE_FACT_DAILY_BRIEF = {
    "mode": "fact",
    "date": "2026-09-03",
    "window": "1.day",
    "total_diffstat": 6364,
    "files_touched": ["scripts/classify.py", "docs/BACKLOG.md"],
    "commit_messages": [
        "feat(author): first MVP pilot (Collector-manifest-based)",
        "fix(classify): scope value classification to collector's own engineering logic",
    ],
    "per_repo": [
        {"name": "article-pipeline", "commit_count": 2, "diffstat": 929, "files_touched": ["docs/BACKLOG.md"]},
    ],
    "decision_source": "heuristic",
}

SAMPLE_IDEA_FALLBACK_DAILY_BRIEF = {
    "mode": "idea_fallback",
    "date": "2026-09-04",
    "window": "1.day",
    "total_diffstat": 3,
    "files_touched": ["x.py"],
    "commit_messages": ["wip"],
    "per_repo": [
        {"name": "collector", "commit_count": 1, "diffstat": 3, "files_touched": ["x.py"]},
    ],
    "decision_source": "heuristic",
}


def _fake_response(payload: dict):
    import json as _json
    content_block = mock.Mock()
    content_block.text = _json.dumps(payload)
    fake_response = mock.Mock()
    fake_response.content = [content_block]
    return fake_response


def test_fact_mode_builds_fact_prompt_and_parses_wellformed_response():
    prompt = author_llm.build_prompt(SAMPLE_FACT_DAILY_BRIEF)
    assert "FACT" in prompt
    assert "EMERGENT PROPERTY" in prompt
    assert "INVERSION" in prompt
    assert "COMMERCIAL HYPOTHESIS" in prompt
    # Real DailyBrief data must actually appear in the prompt, not be
    # dropped or replaced with a placeholder.
    assert "6364" in prompt
    assert "feat(author): first MVP pilot (Collector-manifest-based)" in prompt

    fake_payload = {
        "post": "Saw something odd in today's diff...",
        "fact_or_product": "929-line diffstat in article-pipeline",
        "emergent_property": "some emergent property",
        "inversion": "some inversion",
        "commercial_hypothesis": "I suspect that...",
    }
    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _fake_response(fake_payload)
        response = author_llm.call_model(prompt)

    assert response == fake_payload
    author_llm.validate_structured_response(response, "fact")  # must not raise
    mock_client.messages.create.assert_called_once()
    assert mock_client.messages.create.call_args.kwargs["model"] == author_llm.MODEL


def test_idea_fallback_mode_builds_idea_prompt_and_parses_wellformed_response():
    prompt = author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF)
    for product in author_llm.IDEA_FALLBACK_PRODUCTS:
        assert product in prompt, f"expected product {product!r} to be listed in the idea_fallback prompt"
    assert "reimagin" in prompt.lower()  # "reimagine"/"reimagining"

    fake_payload = {
        "post": "Collector already tracks...",
        "fact_or_product": "Collector",
        "emergent_property": "a reimagined use",
        "evidence_to_collect": "what would validate demand",
    }
    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _fake_response(fake_payload)
        response = author_llm.call_model(prompt)

    assert response == fake_payload
    author_llm.validate_structured_response(response, "idea_fallback")  # must not raise


def test_missing_api_key_env_var_raises_fail_fast_error_not_bare_keyerror():
    env_without_key = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY_DAILY_AUTHOR"}
    with mock.patch.dict(os.environ, env_without_key, clear=True):
        try:
            author_llm._get_api_key()
            raise AssertionError("expected AuthorLLMError, got no exception")
        except author_llm.AuthorLLMError as e:
            assert "ANTHROPIC_API_KEY_DAILY_AUTHOR" in str(e), f"error message must name the env var, got: {e}"
        except KeyError:
            raise AssertionError("must raise AuthorLLMError, not a bare KeyError")


def test_malformed_response_missing_keys_raises_clear_error():
    incomplete_payload = {"post": "some text"}  # missing fact_or_product/emergent_property/etc.
    try:
        author_llm.validate_structured_response(incomplete_payload, "fact")
        raise AssertionError("expected AuthorLLMError for a response missing required keys")
    except author_llm.AuthorLLMError as e:
        assert "fact_or_product" in str(e), f"error should name the missing key(s), got: {e}"


def test_non_json_response_raises_clear_error_not_silent_fallback():
    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        content_block = mock.Mock()
        content_block.text = "this is not json at all"
        fake_response = mock.Mock()
        fake_response.content = [content_block]
        mock_client.messages.create.return_value = fake_response

        try:
            author_llm.call_model("irrelevant prompt")
            raise AssertionError("expected AuthorLLMError for a non-JSON model response")
        except author_llm.AuthorLLMError as e:
            assert "not valid JSON" in str(e), f"error should say the response wasn't valid JSON, got: {e}"


def test_unknown_mode_raises_clear_error():
    try:
        author_llm.build_prompt({"mode": "silence", "total_diffstat": 0})
        raise AssertionError("expected AuthorLLMError for an unknown mode")
    except author_llm.AuthorLLMError as e:
        assert "silence" in str(e)


if __name__ == "__main__":
    tests = [
        test_fact_mode_builds_fact_prompt_and_parses_wellformed_response,
        test_idea_fallback_mode_builds_idea_prompt_and_parses_wellformed_response,
        test_missing_api_key_env_var_raises_fail_fast_error_not_bare_keyerror,
        test_malformed_response_missing_keys_raises_clear_error,
        test_non_json_response_raises_clear_error_not_silent_fallback,
        test_unknown_mode_raises_clear_error,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {test.__name__}: {e}")

    print()
    if failures:
        print(f"{failures}/{len(tests)} test(s) FAILED")
        raise SystemExit(1)
    else:
        print(f"All {len(tests)} test(s) passed")
