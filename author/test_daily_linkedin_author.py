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
    content_block.type = "text"  # must be set explicitly: a bare Mock()
    # auto-vivifies .type as a new Mock object, not the string "text",
    # which would fail _extract_text_block's type check silently.
    content_block.text = _json.dumps(payload)
    fake_response = mock.Mock()
    fake_response.content = [content_block]
    return fake_response


def test_fact_mode_builds_fact_prompt_and_parses_wellformed_response():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
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
    assert mock_client.messages.create.call_args.kwargs["max_tokens"] == 4096


def test_idea_fallback_mode_builds_idea_prompt_and_parses_wellformed_response():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
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


def test_fact_prompt_contains_adr_0044_voice_contract():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = author_llm.build_prompt(SAMPLE_FACT_DAILY_BRIEF)

    # Structure.
    assert "Narrative Bridge 30/40/30" in prompt
    assert "hook" in prompt.lower()
    assert "CTA" in prompt
    # Length.
    assert "150-250 words" in prompt
    assert "max 3 sentences/paragraph" in prompt
    # Voice.
    assert "first person" in prompt
    assert "active voice" in prompt
    assert "no hashtags" in prompt
    assert "0-1 emoji" in prompt
    assert "self-deprecating" in prompt
    # Forbidden vocabulary.
    for forbidden in ("metadiscourse", "nominalizations", "hedge words",
                       "delve", "tapestry", "revolutionize", "game-changer",
                       "low-hanging fruit"):
        assert forbidden in prompt, f"expected forbidden-vocabulary term {forbidden!r} in prompt"
    # Narrowed hedging scope (2026-09-04 content review): hedge words are
    # reserved for the commercial/speculative conclusion only.
    assert "Hedging scope" in prompt
    assert "are reserved" in prompt
    assert "for the final commercial/speculative conclusion only" in prompt
    # Causal chain rule, and the diff-size-metrics-aren't-persuasive rule.
    assert "Causal chain rule" in prompt
    assert "Diffstat and raw lines-changed counts may" in prompt
    assert "never as the evidence doing the" in prompt
    assert "persuasive work" in prompt
    # Explicit feedback-loop shape connecting mechanism to inversion
    # (2026-09-04 content review, not a direct jump).
    assert "explicit feedback loop, not a direct jump" in prompt
    assert (
        "mechanism -> less manual effort -> cheaper/faster check -> more\n"
        "   checks possible -> fewer bad outcomes slip through -> compounding\n"
        "   effect" in prompt
    )
    # CTA rule.
    assert "one open question, in-body, no direct pitch" in prompt
    # Evidence tiers.
    assert "L1 internal" in prompt
    assert "L3 market signal" in prompt
    assert "never fabricated" in prompt


def test_idea_fallback_prompt_contains_adr_0044_voice_contract():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF)
    assert "Narrative Bridge 30/40/30" in prompt
    assert "150-250 words" in prompt
    assert "delve" in prompt
    assert "Causal chain rule" in prompt
    assert "Hedging scope" in prompt
    assert "feedback loop genuinely applies to the reimagined" in prompt


def test_evidence_links_included_for_public_repo_only():
    def fake_visibility(repo_name):
        return repo_name == "article-pipeline"

    with mock.patch.object(author_llm, "_check_repo_visibility", side_effect=fake_visibility):
        prompt = author_llm.build_prompt(SAMPLE_FACT_DAILY_BRIEF)

    assert "https://github.com/mikkiola/article-pipeline" in prompt
    assert "L2 evidence — public repo links confirmed available today" in prompt


def test_evidence_links_block_omits_silently_when_no_repo_public():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = author_llm.build_prompt(SAMPLE_FACT_DAILY_BRIEF)

    assert "https://github.com/mikkiola/" not in prompt
    assert "L2 evidence — no public repo links are confirmed available today" in prompt
    # The evidence block itself carries no apology wording (VOICE_CONTRACT's
    # own meta-rule text legitimately contains the word "apology" — this
    # checks the rendered evidence block specifically, not the whole prompt).
    evidence_block = author_llm._evidence_links_block([])
    assert "sorry" not in evidence_block.lower()
    assert "apolog" not in evidence_block.lower()
    assert "unfortunately" not in evidence_block.lower()


def test_check_repo_visibility_true_for_public_repo():
    fake_result = mock.Mock(returncode=0, stdout='{"visibility": "PUBLIC"}', stderr="")
    with mock.patch("daily_linkedin_author.subprocess.run", return_value=fake_result) as mock_run:
        assert author_llm._check_repo_visibility("article-pipeline") is True
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == ["gh", "repo", "view", "mikkiola/article-pipeline", "--json", "visibility"]


def test_check_repo_visibility_false_for_private_repo():
    fake_result = mock.Mock(returncode=0, stdout='{"visibility": "PRIVATE"}', stderr="")
    with mock.patch("daily_linkedin_author.subprocess.run", return_value=fake_result):
        assert author_llm._check_repo_visibility("some-private-repo") is False


def test_check_repo_visibility_false_on_nonzero_exit():
    fake_result = mock.Mock(returncode=1, stdout="", stderr="repo not found")
    with mock.patch("daily_linkedin_author.subprocess.run", return_value=fake_result):
        assert author_llm._check_repo_visibility("missing-repo") is False


def test_check_repo_visibility_false_on_gh_missing():
    with mock.patch("daily_linkedin_author.subprocess.run", side_effect=FileNotFoundError("gh not found")):
        assert author_llm._check_repo_visibility("article-pipeline") is False


def test_check_repo_visibility_false_on_timeout():
    import subprocess as _subprocess
    with mock.patch("daily_linkedin_author.subprocess.run",
                     side_effect=_subprocess.TimeoutExpired(cmd="gh", timeout=10)):
        assert author_llm._check_repo_visibility("article-pipeline") is False


def test_check_repo_visibility_false_on_unparseable_json():
    fake_result = mock.Mock(returncode=0, stdout="not json", stderr="")
    with mock.patch("daily_linkedin_author.subprocess.run", return_value=fake_result):
        assert author_llm._check_repo_visibility("article-pipeline") is False


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
        content_block.type = "text"
        content_block.text = "this is not json at all"
        fake_response = mock.Mock()
        fake_response.content = [content_block]
        mock_client.messages.create.return_value = fake_response

        try:
            author_llm.call_model("irrelevant prompt")
            raise AssertionError("expected AuthorLLMError for a non-JSON model response")
        except author_llm.AuthorLLMError as e:
            assert "not valid JSON" in str(e), f"error should say the response wasn't valid JSON, got: {e}"


def test_call_model_skips_leading_thinking_block_and_extracts_text_block():
    # Regression test for the real bug the 2026-09-03 live run found:
    # response.content can carry a ThinkingBlock ahead of the TextBlock
    # when extended thinking is involved — call_model() must find the
    # text block by .type, not assume it's content[0].
    payload = {
        "post": "text after a thinking block",
        "fact_or_product": "x",
        "emergent_property": "x",
        "inversion": "x",
        "commercial_hypothesis": "x",
    }
    import json as _json
    thinking_block = mock.Mock(spec=["type"])  # deliberately no .text attribute at all
    thinking_block.type = "thinking"
    text_block = mock.Mock()
    text_block.type = "text"
    text_block.text = _json.dumps(payload)

    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        fake_response = mock.Mock()
        fake_response.content = [thinking_block, text_block]
        mock_client.messages.create.return_value = fake_response
        response = author_llm.call_model("irrelevant prompt")

    assert response == payload


def test_call_model_raises_clear_error_when_no_text_block_present():
    thinking_block = mock.Mock(spec=["type"])
    thinking_block.type = "thinking"

    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        fake_response = mock.Mock()
        fake_response.content = [thinking_block]
        mock_client.messages.create.return_value = fake_response

        try:
            author_llm.call_model("irrelevant prompt")
            raise AssertionError("expected AuthorLLMError when no text block is present")
        except AttributeError:
            raise AssertionError("must raise AuthorLLMError, not a bare AttributeError")
        except author_llm.AuthorLLMError as e:
            assert "thinking" in str(e), f"error should name the block type(s) actually found, got: {e}"


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
        test_fact_prompt_contains_adr_0044_voice_contract,
        test_idea_fallback_prompt_contains_adr_0044_voice_contract,
        test_evidence_links_included_for_public_repo_only,
        test_evidence_links_block_omits_silently_when_no_repo_public,
        test_check_repo_visibility_true_for_public_repo,
        test_check_repo_visibility_false_for_private_repo,
        test_check_repo_visibility_false_on_nonzero_exit,
        test_check_repo_visibility_false_on_gh_missing,
        test_check_repo_visibility_false_on_timeout,
        test_check_repo_visibility_false_on_unparseable_json,
        test_missing_api_key_env_var_raises_fail_fast_error_not_bare_keyerror,
        test_malformed_response_missing_keys_raises_clear_error,
        test_non_json_response_raises_clear_error_not_silent_fallback,
        test_call_model_skips_leading_thinking_block_and_extracts_text_block,
        test_call_model_raises_clear_error_when_no_text_block_present,
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
