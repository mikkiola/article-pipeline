#!/usr/bin/env python3
"""Plain-assert tests for daily_linkedin_author.py.

Run: python3 test_daily_linkedin_author.py

Matches this directory's own test_pipeline.py convention (plain
asserts, no framework). No real API call is ever made — the Anthropic
client is mocked in every test that reaches call_model().
"""

import contextlib
import io
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
        {"name": "article-pipeline", "commit_count": 2, "diffstat": 929, "files_touched": ["docs/BACKLOG.md"],
         "commit_messages": [
             "feat(author): first MVP pilot (Collector-manifest-based)",
             "fix(classify): scope value classification to collector's own engineering logic",
         ]},
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
    # Facts-only structure (temporary, 2026-09-24): the old FACT/EMERGENT
    # PROPERTY/INVERSION/COMMERCIAL HYPOTHESIS steps are gone.
    assert "Repo/context" in prompt
    assert "EMERGENT PROPERTY" not in prompt
    # Real DailyBrief data must actually appear in the prompt, as an
    # ID-tagged cluster fact, not be dropped or replaced with a placeholder.
    assert "article-pipeline:fact_01" in prompt
    assert "feat(author): first MVP pilot (Collector-manifest-based)" in prompt

    fake_payload = {
        "post": "Saw something odd in today's diff...",
        "fact_or_product": "the MVP pilot commit in article-pipeline",
        "selected_cluster": "article-pipeline",
        "supporting_facts": ["article-pipeline:fact_01", "article-pipeline:fact_02"],
    }
    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = _fake_response(fake_payload)
        response = author_llm.call_model(prompt)

    assert response == fake_payload
    author_llm.validate_structured_response(
        response, "fact", SAMPLE_FACT_DAILY_BRIEF
    )  # must not raise
    mock_client.messages.create.assert_called_once()
    assert mock_client.messages.create.call_args.kwargs["model"] == author_llm.MODEL
    assert mock_client.messages.create.call_args.kwargs["max_tokens"] == 4096
    assert mock_client.messages.create.call_args.kwargs["thinking"] == {"type": "disabled"}


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


# --- Temporary facts-only fact prompt (owner request, 2026-09-24) ---------
# Replaces test_fact_prompt_contains_adr_0044_voice_contract: the fact
# prompt deliberately no longer implements ADR-0044's Narrative Bridge
# structure. The fallback prompt still does — see its test below.

SYNTHETIC_FACTS_BRIEF = {
    "mode": "fact",
    "date": "2026-09-24",
    "window": "1.day",
    "total_diffstat": 1000,
    "files_touched": ["a.py", "b.py", "docs/x.md", "c/d.py", "e.txt"],
    "commit_messages": [
        "feat(publication_registry): content_id becomes caller-supplied (ADR-0053)",
        "docs(architecture): add Publication Registry row",
        "fix(linkedin_publisher): bump expired LinkedIn-Version header",
    ],
    "per_repo": [
        {"name": "article-pipeline", "commit_count": 3, "diffstat": 1000,
         "files_touched": ["a.py", "b.py", "docs/x.md", "c/d.py", "e.txt"],
         "commit_messages": [
             "feat(publication_registry): content_id becomes caller-supplied (ADR-0053)",
             "docs(architecture): add Publication Registry row",
             "fix(linkedin_publisher): bump expired LinkedIn-Version header",
         ]},
        {"name": "radar", "commit_count": 0, "diffstat": 0, "files_touched": [],
         "commit_messages": []},
    ],
    "decision_source": "heuristic",
}


def _facts_prompt():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        return " ".join(author_llm.build_prompt(SYNTHETIC_FACTS_BRIEF).split())


def test_fact_prompt_has_facts_only_shape_and_drops_removed_instructions():
    prompt = _facts_prompt()
    # Target shape, in order: repo/context -> change -> evidence -> question.
    positions = [prompt.index(f"{n}. {name}") for n, name in
                 ((1, "Repo/context"), (2, "Change"), (3, "Evidence"), (4, "Question"))]
    assert positions == sorted(positions)
    assert "exactly one open question" in prompt
    assert "No greeting" in prompt
    assert "100-200 words" in prompt
    assert "Maximum 3 sentences per paragraph" in prompt
    assert "First person, active voice" in prompt
    assert "No hashtags" in prompt and "No emoji" in prompt
    # Removed instruction texts must be gone.
    for removed in (
        "EMERGENT PROPERTY", "INVERSION", "COMMERCIAL HYPOTHESIS",
        "Narrative Bridge", "30/40/30", "L3 market signal", "Bridge (~40%",
        "feedback loop", "150-250", '"emergent_property"', '"inversion"',
        '"commercial_hypothesis"',
    ):
        assert removed not in prompt, f"removed instruction text still present: {removed!r}"
    # Real input still reaches the model as ID-tagged cluster facts, and
    # counts are computed in code. Diffstat is not offered as a fact.
    assert "feat(publication_registry): content_id becomes caller-supplied" in prompt
    assert "article-pipeline:fact_04 (commit count): 3" in prompt
    assert "article-pipeline:fact_05 (files touched count): 5" in prompt
    assert "1000" not in prompt


def test_fact_prompt_says_no_reason_if_the_input_has_none():
    prompt = _facts_prompt()
    assert (
        "If the input does not contain a reason for a change, say nothing about a reason"
        in prompt
    )
    assert "If the data contains no reason, the post states none" in prompt
    assert "ONLY source of facts" in prompt
    assert "Never invent a number" in prompt


def test_fact_prompt_states_the_evidence_boundary_explicitly():
    prompt = _facts_prompt()
    assert "Only use information present in the supplied data above" in prompt
    assert (
        "Do not infer or invent the author's motivation, reason, consequence, "
        "or lesson from a commit subject, a diffstat, or a file path"
    ) in prompt
    assert (
        "a commit subject describes what changed; it does not establish why it "
        "was changed"
    ) in prompt
    assert (
        "If the supplied data does not contain a reason, do not state one, "
        "imply one, or hint that one exists"
    ) in prompt


def test_fact_prompt_stays_silent_about_commit_body_trailers():
    # Why:/Effect: trailer lines are deliberately not an accepted source yet,
    # so the prompt must not mention them at all.
    prompt = _facts_prompt()
    assert "Why:" not in prompt
    assert "Effect:" not in prompt
    assert "trailer" not in prompt.lower()


def test_evidence_boundary_text_is_not_added_to_the_idea_fallback_prompt():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = " ".join(author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF).split())
    assert "it does not establish why it was changed" not in prompt


def test_fact_prompt_forbids_naming_adr_numbers():
    prompt = _facts_prompt()
    assert "Do not name ADR numbers, even if a commit subject contains one" in prompt
    assert "Do not name ADR numbers as evidence" in prompt


def test_fact_prompt_keeps_the_l2_public_link_mechanism():
    def fake_visibility(repo_name):
        return repo_name == "article-pipeline"

    with mock.patch.object(author_llm, "_check_repo_visibility", side_effect=fake_visibility):
        prompt = author_llm.build_prompt(SYNTHETIC_FACTS_BRIEF)
    assert "https://github.com/mikkiola/article-pipeline" in prompt
    assert "https://github.com/mikkiola/radar" not in prompt


def test_fact_response_requires_post_fact_or_product_and_the_cluster_keys():
    assert author_llm.FACT_REQUIRED_KEYS == {
        "post", "fact_or_product", "selected_cluster", "supporting_facts",
    }
    author_llm.validate_structured_response(
        {"post": "I pushed 3 commits to article-pipeline.", "fact_or_product": "x",
         "selected_cluster": "article-pipeline",
         "supporting_facts": ["article-pipeline:fact_01"]},
        "fact", SYNTHETIC_FACTS_BRIEF,
    )  # must not raise
    for missing in ("fact_or_product", "selected_cluster", "supporting_facts"):
        full = {"post": "text", "fact_or_product": "x", "selected_cluster": "article-pipeline",
                "supporting_facts": ["article-pipeline:fact_01"]}
        del full[missing]
        try:
            author_llm.validate_structured_response(full, "fact", SYNTHETIC_FACTS_BRIEF)
            raise AssertionError(f"expected AuthorLLMError for a missing {missing}")
        except author_llm.AuthorLLMError as e:
            assert missing in str(e)


# --- Experiment 1: per-repo clusters, stable fact IDs, ID-based verification ---
# Deterministic repo-based clustering only. ADR-0057's inference boundary is
# untouched by this change (its own tests above still pin that wording).

TWO_CLUSTER_BRIEF = {
    "mode": "fact",
    "date": "2026-09-26",
    "total_diffstat": 50,
    "files_touched": ["a.py", "b.md", "c.py"],
    "commit_messages": ["fix: alpha", "feat: beta", "docs: gamma"],
    "per_repo": [
        {"name": "collector", "commit_count": 2, "diffstat": 30, "files_touched": ["a.py", "b.md"],
         "commit_messages": ["fix: alpha", "feat: beta"]},
        {"name": "brain", "commit_count": 1, "diffstat": 20, "files_touched": ["c.py"],
         "commit_messages": ["docs: gamma"]},
        {"name": "radar", "commit_count": 0, "diffstat": 0, "files_touched": [],
         "commit_messages": []},
    ],
}


def _cluster_prompt(brief):
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        return " ".join(author_llm.build_prompt(brief).split())


def _cited(post_cluster, facts):
    return {"post": "I pushed commits.", "fact_or_product": "x",
            "selected_cluster": post_cluster, "supporting_facts": facts}


def test_build_clusters_assigns_stable_per_repo_fact_ids_to_the_exact_data_points():
    clusters = author_llm.build_clusters(SYNTHETIC_FACTS_BRIEF)
    assert [c["repo"] for c in clusters] == ["article-pipeline"]
    facts = clusters[0]["facts"]
    assert [f["id"] for f in facts] == [
        "article-pipeline:fact_01", "article-pipeline:fact_02", "article-pipeline:fact_03",
        "article-pipeline:fact_04", "article-pipeline:fact_05",
    ]
    # Subjects are the data points exactly as they appear, in order, unreworded.
    assert [f["text"] for f in facts[:3]] == SYNTHETIC_FACTS_BRIEF["per_repo"][0]["commit_messages"]
    assert (facts[3]["kind"], facts[3]["text"]) == ("commit count", "3")
    assert (facts[4]["kind"], facts[4]["text"]) == ("files touched count", "5")


def test_repo_with_zero_commits_forms_no_cluster_and_is_never_offered():
    assert [c["repo"] for c in author_llm.build_clusters(SYNTHETIC_FACTS_BRIEF)] == ["article-pipeline"]
    prompt = _cluster_prompt(SYNTHETIC_FACTS_BRIEF)
    assert "radar" not in prompt
    assert [c["repo"] for c in author_llm.build_clusters(TWO_CLUSTER_BRIEF)] == ["collector", "brain"]
    assert "radar" not in _cluster_prompt(TWO_CLUSTER_BRIEF)


def test_fact_prompt_offers_only_id_tagged_clusters_not_a_flat_cross_repo_list():
    prompt = _cluster_prompt(TWO_CLUSTER_BRIEF)
    assert "Cluster: collector" in prompt and "Cluster: brain" in prompt
    assert prompt.index('collector:fact_01 (commit subject): "fix: alpha"') < prompt.index("Cluster: brain")
    assert 'brain:fact_01 (commit subject): "docs: gamma"' in prompt
    # The old flat cross-repo dump is gone.
    for gone in ("- commit_messages:", "per_repo breakdown", "total commits:",
                 "repositories with commits:", "- total_diffstat:", "- files_touched:"):
        assert gone not in prompt, f"flat-shape text still present: {gone!r}"
    # Each repository's messages sit only in its own cluster.
    assert prompt.index("docs: gamma") > prompt.index("Cluster: brain")


def test_fact_prompt_asks_for_one_cluster_with_neutral_selection_wording():
    prompt = _cluster_prompt(TWO_CLUSTER_BRIEF)
    assert "Select exactly ONE cluster" in prompt
    assert ("select one repository whose cluster contains enough related facts "
            "to form a coherent post") in prompt
    assert "If more than one cluster qualifies, any one of them is acceptable" in prompt
    assert "Do not mention facts, changes, or repositories from any other cluster" in prompt
    for evaluative in ("most interesting", "best cluster", "most important", "most relevant"):
        assert evaluative not in prompt.lower()
    assert "connect 2-3 of the selected cluster's facts into one connected paragraph" in prompt
    assert ("Connecting facts does not permit stating why something was done, "
            "what it leads to, or what it means") in prompt
    assert '"selected_cluster"' in prompt and '"supporting_facts"' in prompt


def test_prompt_build_fails_loudly_when_per_repo_has_no_commit_messages_key():
    old_shape = {"mode": "fact", "date": "d", "total_diffstat": 1, "files_touched": ["a"],
                 "commit_messages": ["m"],
                 "per_repo": [{"name": "collector", "commit_count": 1, "diffstat": 1,
                               "files_touched": ["a"]}]}
    try:
        _cluster_prompt(old_shape)
        raise AssertionError("expected AuthorLLMError for a per_repo entry with no commit_messages")
    except author_llm.AuthorLLMError as e:
        assert "collector" in str(e) and "commit_messages" in str(e)


def test_prompt_build_fails_loudly_when_no_repo_has_any_commit():
    empty = {"mode": "fact", "date": "d", "total_diffstat": 0, "files_touched": [],
             "commit_messages": [],
             "per_repo": [{"name": "radar", "commit_count": 0, "diffstat": 0,
                           "files_touched": [], "commit_messages": []}]}
    try:
        _cluster_prompt(empty)
        raise AssertionError("expected AuthorLLMError when no cluster can be offered")
    except author_llm.AuthorLLMError as e:
        assert "cluster" in str(e)


def test_well_formed_cluster_citation_passes_validation():
    author_llm.validate_structured_response(
        _cited("collector", ["collector:fact_01", "collector:fact_03"]), "fact", TWO_CLUSTER_BRIEF
    )  # must not raise


def _assert_rejected(response, brief, expected_fragment):
    try:
        author_llm.validate_structured_response(response, "fact", brief)
        raise AssertionError(f"expected AuthorLLMError containing {expected_fragment!r}")
    except author_llm.AuthorLLMError as e:
        assert expected_fragment in str(e), f"got: {e}"


def test_selected_cluster_that_was_not_offered_is_rejected():
    _assert_rejected(_cited("nonexistent", ["collector:fact_01"]), TWO_CLUSTER_BRIEF, "selected_cluster")
    # A repo that had zero commits was never offered, so it cannot be selected.
    _assert_rejected(_cited("radar", ["radar:fact_01"]), TWO_CLUSTER_BRIEF, "selected_cluster")
    _assert_rejected(_cited(["collector"], ["collector:fact_01"]), TWO_CLUSTER_BRIEF, "selected_cluster")


def test_fact_id_from_a_cluster_not_offered_this_run_is_rejected():
    _assert_rejected(_cited("collector", ["radar:fact_01"]), TWO_CLUSTER_BRIEF, "radar:fact_01")
    _assert_rejected(_cited("collector", ["ghost-repo:fact_01"]), TWO_CLUSTER_BRIEF, "ghost-repo:fact_01")


def test_fact_id_from_another_offered_cluster_is_rejected():
    _assert_rejected(_cited("collector", ["collector:fact_01", "brain:fact_01"]),
                     TWO_CLUSTER_BRIEF, "brain:fact_01")


def test_fact_id_that_does_not_exist_in_the_selected_cluster_is_rejected():
    _assert_rejected(_cited("collector", ["collector:fact_99"]), TWO_CLUSTER_BRIEF, "collector:fact_99")
    # Exact string match only: no fuzzy or semantic matching of IDs.
    _assert_rejected(_cited("collector", ["Collector:fact_01"]), TWO_CLUSTER_BRIEF, "Collector:fact_01")
    _assert_rejected(_cited("collector", ["collector:fact_1"]), TWO_CLUSTER_BRIEF, "collector:fact_1")


def test_supporting_facts_must_be_a_non_empty_list_of_strings():
    _assert_rejected(_cited("collector", []), TWO_CLUSTER_BRIEF, "supporting_facts")
    _assert_rejected(_cited("collector", "collector:fact_01"), TWO_CLUSTER_BRIEF, "supporting_facts")
    _assert_rejected(_cited("collector", [["collector:fact_01"]]), TWO_CLUSTER_BRIEF, "supporting_facts")


def test_fact_mode_validation_without_the_daily_brief_fails_closed():
    _assert_rejected(_cited("collector", ["collector:fact_01"]), None, "daily_brief")


def test_idea_fallback_validation_needs_no_daily_brief_and_no_cluster_keys():
    author_llm.validate_structured_response(
        {"post": "Collector already tracks...", "fact_or_product": "Collector",
         "emergent_property": "x", "evidence_to_collect": "y"},
        "idea_fallback",
    )  # must not raise


PLAIN_FACTS_ONLY_POST = (
    "I pushed 3 commits to article-pipeline today.\n\n"
    "One made the Publication Registry accept a caller-supplied content_id. "
    "One added a Registry row to the architecture doc. One updated an expired "
    "LinkedIn API version header.\n\n"
    "5 files changed in total.\n\n"
    "When did you last find a header expiring in your own pipeline?"
)


def test_post_check_rejects_adr_number():
    try:
        author_llm.check_post_content("I changed content_id handling (ADR-0053) today.")
        raise AssertionError("expected AuthorLLMError for a post naming an ADR number")
    except author_llm.AuthorLLMError as e:
        assert "ADR number" in str(e)


def test_post_check_rejects_greeting():
    for greeting_post in ("Hi everyone, today I pushed 3 commits.",
                          "Hello! I pushed 3 commits.",
                          "Hey there. I pushed 3 commits."):
        try:
            author_llm.check_post_content(greeting_post)
            raise AssertionError(f"expected AuthorLLMError for {greeting_post!r}")
        except author_llm.AuthorLLMError as e:
            assert "greeting" in str(e)


def test_post_check_accepts_plain_facts_only_post():
    author_llm.check_post_content(PLAIN_FACTS_ONLY_POST)  # must not raise


def test_post_check_is_applied_by_validate_structured_response_in_both_modes():
    bad = {"post": "Hi all, I pushed commits.", "fact_or_product": "x", "emergent_property": "x",
           "evidence_to_collect": "x", "selected_cluster": "article-pipeline",
           "supporting_facts": ["article-pipeline:fact_01"]}
    for mode in ("fact", "idea_fallback"):
        try:
            author_llm.validate_structured_response(bad, mode)
            raise AssertionError(f"expected AuthorLLMError in mode={mode}")
        except author_llm.AuthorLLMError as e:
            assert "greeting" in str(e)


def test_idea_fallback_prompt_contains_adr_0044_voice_contract():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF)
    assert "Narrative Bridge 30/40/30" in prompt
    assert "150-250 words" in prompt
    assert "delve" in prompt
    assert "Causal chain rule" in prompt
    assert "Hedging scope" in prompt
    assert "feedback loop genuinely applies to the reimagined" in prompt


# sha256 of the fallback prompt built from SAMPLE_IDEA_FALLBACK_DAILY_BRIEF
# (repo visibility mocked to False), captured from the code as it stood at
# commit 61ee40d, BEFORE the temporary facts-only change. If this fails,
# the fallback prompt (or STYLE_CONSTRAINTS/VOICE_CONTRACT it embeds)
# changed — update the hash only if that change is intentional.
ORIGINAL_FALLBACK_PROMPT_SHA256 = "21601201862ba5c35716c18ccc59ab81ec36203dc9bd2322a1aaa38c0921d52e"


def test_idea_fallback_prompt_is_unchanged_by_the_facts_only_change():
    import hashlib
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF)
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == ORIGINAL_FALLBACK_PROMPT_SHA256


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


def test_call_model_disables_thinking_and_logs_stop_reason():
    # Regression test: claude-sonnet-5 runs with adaptive thinking
    # (effort: high) by default unless thinking={"type": "disabled"}
    # is explicitly passed — a real production run omitted this and
    # exhausted the entire max_tokens budget on a thinking block with
    # zero text output (block_types: ['thinking'], 2026-09-24 workflow
    # run). Also confirms stop_reason is now logged, closing the
    # diagnostic gap that made that failure take three review rounds
    # to actually root-cause (stop_reason was never visible anywhere).
    fake_payload = {
        "post": "some post",
        "fact_or_product": "x",
        "emergent_property": "x",
        "inversion": "x",
        "commercial_hypothesis": "x",
    }
    fake_response = _fake_response(fake_payload)
    fake_response.stop_reason = "end_turn"

    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = fake_response

        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            author_llm.call_model("irrelevant prompt")

    assert mock_client.messages.create.call_args.kwargs["thinking"] == {"type": "disabled"}
    assert "stop_reason: end_turn" in captured.getvalue()


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
        test_fact_prompt_has_facts_only_shape_and_drops_removed_instructions,
        test_fact_prompt_says_no_reason_if_the_input_has_none,
        test_fact_prompt_forbids_naming_adr_numbers,
        test_fact_prompt_keeps_the_l2_public_link_mechanism,
        test_fact_response_requires_post_fact_or_product_and_the_cluster_keys,
        test_build_clusters_assigns_stable_per_repo_fact_ids_to_the_exact_data_points,
        test_repo_with_zero_commits_forms_no_cluster_and_is_never_offered,
        test_fact_prompt_offers_only_id_tagged_clusters_not_a_flat_cross_repo_list,
        test_fact_prompt_asks_for_one_cluster_with_neutral_selection_wording,
        test_prompt_build_fails_loudly_when_per_repo_has_no_commit_messages_key,
        test_prompt_build_fails_loudly_when_no_repo_has_any_commit,
        test_well_formed_cluster_citation_passes_validation,
        test_selected_cluster_that_was_not_offered_is_rejected,
        test_fact_id_from_a_cluster_not_offered_this_run_is_rejected,
        test_fact_id_from_another_offered_cluster_is_rejected,
        test_fact_id_that_does_not_exist_in_the_selected_cluster_is_rejected,
        test_supporting_facts_must_be_a_non_empty_list_of_strings,
        test_fact_mode_validation_without_the_daily_brief_fails_closed,
        test_idea_fallback_validation_needs_no_daily_brief_and_no_cluster_keys,
        test_post_check_rejects_adr_number,
        test_post_check_rejects_greeting,
        test_post_check_accepts_plain_facts_only_post,
        test_post_check_is_applied_by_validate_structured_response_in_both_modes,
        test_idea_fallback_prompt_is_unchanged_by_the_facts_only_change,
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
        test_call_model_disables_thinking_and_logs_stop_reason,
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
