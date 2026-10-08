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
    # ADR-0059 five-step reasoning structure: the old EMERGENT PROPERTY/
    # INVERSION/COMMERCIAL HYPOTHESIS steps stay gone (INVERSION is
    # explicitly not restored, ADR-0059 Decision point 5).
    assert "1. FACT" in prompt
    assert "EMERGENT PROPERTY" not in prompt
    # Real DailyBrief data must actually appear in the prompt, as an
    # ID-tagged cluster fact, not be dropped or replaced with a placeholder.
    assert "article-pipeline:fact_01" in prompt
    assert "feat(author): first MVP pilot (Collector-manifest-based)" in prompt

    fake_payload = {
        "automation_only_day": False,
        "post": "Saw something odd in today's diff...",
        "selected_cluster": "article-pipeline",
        "supporting_facts": ["article-pipeline:fact_01", "article-pipeline:fact_02"],
        "reasoning": {
            "fact": "Two commits landed in article-pipeline.",
            "tension": "A pilot feature and a scoping fix landed together.",
            "design_insight": "The author treats scope correction as part of shipping, not cleanup.",
            "personal_position": "I want scope drift caught before it needs its own commit.",
            "relevant_problem": "Teams may ship features whose scope quietly widens unnoticed.",
        },
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


# --- Fact prompt (ADR-0059: five-step evidence-grounded reasoning) --------
# Replaces test_fact_prompt_contains_adr_0044_voice_contract: the fact
# prompt deliberately no longer implements ADR-0044's Narrative Bridge
# structure. The fallback prompt still does — see its test below. Also
# replaces the ADR-0057 facts-only structure's own tests (2026-09-24 —
# 2026-09-29): ADR-0059 lifted that structure's blanket reasoning
# prohibition, see docs/adr/0059-....md.

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


def _facts_prompt(identity_state=None, recent_posts=None):
    # Explicit empty defaults here, not None: existing callers of this
    # helper must stay deterministic regardless of whatever real state
    # happens to be on disk under author/state/ — real-file loading is
    # exercised separately, below, by tests that mock the load functions.
    if identity_state is None:
        identity_state = dict(author_llm.identity_state_module.DEFAULT_IDENTITY_STATE)
    if recent_posts is None:
        recent_posts = []
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        return " ".join(author_llm.build_prompt(
            SYNTHETIC_FACTS_BRIEF, identity_state=identity_state, recent_posts=recent_posts
        ).split())


def test_fact_prompt_has_five_step_reasoning_shape_in_order():
    prompt = _facts_prompt()
    # Target shape, in order: FACT -> TENSION -> DESIGN INSIGHT ->
    # PERSONAL POSITION -> RELEVANT PROBLEM, then a FINAL EVIDENCE CHECK
    # step (ADR-0059 Decision point 4).
    positions = [prompt.index(f"{n}. {name}") for n, name in
                 ((1, "FACT"), (2, "TENSION"), (3, "DESIGN INSIGHT"),
                  (4, "PERSONAL POSITION"), (5, "RELEVANT PROBLEM"))]
    assert positions == sorted(positions)
    assert positions[-1] < prompt.index("FINAL EVIDENCE CHECK")
    assert "150-300 words" in prompt
    assert "Maximum 3 sentences per paragraph" in prompt
    assert "First person, active voice" in prompt
    assert "No hashtags" in prompt and "No emoji" in prompt and "No greeting" in prompt
    # INVERSION is explicitly not restored (ADR-0059 Decision point 5); the
    # old EMERGENT PROPERTY/COMMERCIAL HYPOTHESIS structure and ADR-0044's
    # Narrative Bridge stay gone too.
    for removed in (
        "EMERGENT PROPERTY", "INVERSION", "COMMERCIAL HYPOTHESIS",
        "Narrative Bridge", "30/40/30", "L3 market signal", "Bridge (~40%",
        "feedback loop", "150-250", '"emergent_property"', '"inversion"',
        '"commercial_hypothesis"', '"fact_or_product"',
    ):
        assert removed not in prompt, f"removed instruction text still present: {removed!r}"
    # Real input still reaches the model as ID-tagged cluster facts, and
    # counts are computed in code. Diffstat is not offered as a fact.
    assert "feat(publication_registry): content_id becomes caller-supplied" in prompt
    assert "article-pipeline:fact_04 (commit count): 3" in prompt
    assert "article-pipeline:fact_05 (files touched count): 5" in prompt
    assert "1000" not in prompt


def test_fact_prompt_each_step_carries_its_own_defining_instruction():
    # test_fact_prompt_has_five_step_reasoning_shape_in_order only pins each
    # step's numbered header and their relative order — it would still pass
    # if a step's own substantive instructions were hollowed out to a single
    # line while its header survived. This pins one load-bearing sentence
    # per step (B-058's third checkbox: "coverage for... each of the five
    # steps"), so a regression that guts a step's actual content, not just
    # its heading, is caught.
    prompt = _facts_prompt()
    assert (
        "Only what is directly supported by its facts. No interpretation, no "
        "inferred reason, no inferred consequence"
    ) in prompt
    assert (
        "identify a concrete, specific gap, mismatch, asymmetry, or unresolved design "
        "question visible in the selected cluster itself"
    ) in prompt
    assert "The insight must preserve the exact object of the tension" in prompt
    assert (
        "The position must still originate from today's tension, but may be broader "
        "than what today's data proves"
    ) in prompt
    assert (
        "framed explicitly as an untested hypothesis, never as a confirmed fact about "
        "any market, product, or user"
    ) in prompt


def test_fact_prompt_final_evidence_check_content_is_present():
    # test_fact_prompt_has_five_step_reasoning_shape_in_order only confirms
    # the FINAL EVIDENCE CHECK heading exists after the five steps — it does
    # not pin what that check actually requires. B-058's third checkbox
    # names "the final evidence check" as its own coverage target,
    # separately from the five steps.
    prompt = _facts_prompt()
    assert (
        'Do not state as fact: absence of a capability or mechanism unless the facts '
        'explicitly establish that absence'
    ) in prompt
    assert (
        'what "nobody", "the team", "the system", or "the author" could or could not do'
    ) in prompt
    assert "If a sentence cannot pass this check, rewrite it conservatively or remove it" in prompt
    assert (
        "This check does not constrain the personal position itself: the evidence "
        "requirement applies to claims about reality, not to the author's stated preference"
    ) in prompt


# --- Automation-only-day guard (ADR-0059 Decision point 7) -----------------
# Prompt-level guard only: the model still gets called, but is told not to
# fabricate a personal position/full post when the selected cluster's
# commits are entirely automated output. B-069's own, separate, still-
# unbuilt scope is skipping the API call before any model call — not
# tested here.


def test_fact_prompt_includes_automation_only_day_guard_prose():
    prompt = _facts_prompt()
    assert (
        "check whether the selected cluster's commits are entirely the output of "
        "an automated, scheduled process with no accompanying manual engineering "
        "work that day"
    ) in prompt
    assert (
        "An automated process's own commit structure is never evidence of the "
        "author's engineering judgment on that day"
    ) in prompt
    assert (
        '"automation_only_day" set to true, "post" set to an empty string, '
        '"supporting_facts" set to an empty list'
    ) in prompt


def test_fact_prompt_output_format_documents_automation_only_day_field():
    prompt = _facts_prompt()
    assert '"automation_only_day": true if the automation-only-day guard above' in prompt
    assert 'Empty only on an automation-only day' in prompt


def test_idea_fallback_prompt_never_mentions_automation_only_day():
    # The guard is fact-mode-only; idea_fallback keeps its own ADR-0044 keys.
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF)
    assert "automation_only_day" not in prompt
    assert "automation-only-day" not in prompt.lower()


_GOOD_AUTOMATION_ONLY_RESPONSE = {
    "automation_only_day": True,
    "post": "",
    "selected_cluster": "article-pipeline",
    "supporting_facts": [],
    "reasoning": {
        "fact": "The selected cluster's only commit was an automated, scheduled "
                "process's own output, with no manual engineering work alongside it.",
        "tension": "", "design_insight": "", "personal_position": "", "relevant_problem": "",
    },
}


def test_automation_only_day_response_well_formed_passes_validation():
    author_llm.validate_structured_response(
        dict(_GOOD_AUTOMATION_ONLY_RESPONSE), "fact", SYNTHETIC_FACTS_BRIEF
    )  # must not raise


def test_automation_only_day_response_rejects_non_empty_post():
    bad = {**_GOOD_AUTOMATION_ONLY_RESPONSE, "post": "I pushed a commit."}
    try:
        author_llm.validate_structured_response(bad, "fact", SYNTHETIC_FACTS_BRIEF)
        raise AssertionError("expected AuthorLLMError for a non-empty post on an automation-only day")
    except author_llm.AuthorLLMError as e:
        assert "post" in str(e)


def test_automation_only_day_response_rejects_non_empty_supporting_facts():
    bad = {**_GOOD_AUTOMATION_ONLY_RESPONSE, "supporting_facts": ["article-pipeline:fact_01"]}
    try:
        author_llm.validate_structured_response(bad, "fact", SYNTHETIC_FACTS_BRIEF)
        raise AssertionError("expected AuthorLLMError for non-empty supporting_facts on an automation-only day")
    except author_llm.AuthorLLMError as e:
        assert "supporting_facts" in str(e)


def test_automation_only_day_response_rejects_cluster_not_offered():
    bad = {**_GOOD_AUTOMATION_ONLY_RESPONSE, "selected_cluster": "nonexistent"}
    try:
        author_llm.validate_structured_response(bad, "fact", SYNTHETIC_FACTS_BRIEF)
        raise AssertionError("expected AuthorLLMError for a selected_cluster not offered this run")
    except author_llm.AuthorLLMError as e:
        assert "selected_cluster" in str(e)


def test_automation_only_day_response_rejects_blank_reasoning_fact():
    bad = {**_GOOD_AUTOMATION_ONLY_RESPONSE,
           "reasoning": {**_GOOD_AUTOMATION_ONLY_RESPONSE["reasoning"], "fact": "   "}}
    try:
        author_llm.validate_structured_response(bad, "fact", SYNTHETIC_FACTS_BRIEF)
        raise AssertionError("expected AuthorLLMError for a blank reasoning.fact")
    except author_llm.AuthorLLMError as e:
        assert "reasoning.fact" in str(e)


def test_automation_only_day_response_rejects_non_empty_other_reasoning_fields():
    bad = {**_GOOD_AUTOMATION_ONLY_RESPONSE,
           "reasoning": {**_GOOD_AUTOMATION_ONLY_RESPONSE["reasoning"], "tension": "a real tension"}}
    try:
        author_llm.validate_structured_response(bad, "fact", SYNTHETIC_FACTS_BRIEF)
        raise AssertionError("expected AuthorLLMError for a non-empty 'tension' on an automation-only day")
    except author_llm.AuthorLLMError as e:
        assert "tension" in str(e)


def test_automation_only_day_true_is_distinguished_from_false_by_type():
    # Only the literal boolean True triggers the automation-only-day path —
    # a truthy-but-wrong-type value must not silently take this shortcut
    # and skip the normal five-step validation it was never meant to.
    normal = _cited("article-pipeline", ["article-pipeline:fact_01"])
    normal["automation_only_day"] = "true"  # a string, not a bool
    author_llm.validate_structured_response(normal, "fact", SYNTHETIC_FACTS_BRIEF)  # must not raise
    # (falls through to normal validation since "true" is not `is True`, and
    # `normal`'s post/citations are otherwise well-formed)


def test_fact_prompt_drops_adr_0057_facts_only_prohibition_language():
    # ADR-0059 Decision point 3 lifts ADR-0057's blanket ban on any
    # reasoning over facts; only the fixed structural order and the
    # blanket "no reason/consequence/insight" language are gone. The
    # underlying no-invented-fact boundary (checked in the next test) is
    # preserved unchanged (ADR-0059 Decision point 2).
    prompt = _facts_prompt()
    for removed in (
        "Repo/context", "Write the post in exactly this order",
        'Do not include a reason ("because...")',
        "exactly one open question",
    ):
        assert removed not in prompt, f"ADR-0057 structural text still present: {removed!r}"


# --- Identity continuity (ADR-0059 Decision point 6) -----------------------


def test_fact_prompt_says_none_recorded_yet_when_no_history_exists():
    prompt = _facts_prompt(identity_state=dict(author_llm.identity_state_module.DEFAULT_IDENTITY_STATE),
                            recent_posts=[])
    assert "none recorded yet" in prompt
    assert "newly forming" in prompt


def test_fact_prompt_includes_identity_state_positions_and_trajectory_when_present():
    state = {
        "core_positions": ["small fixes should land alone"],
        "emerging_positions": ["scope drift deserves its own commit"],
        "recently_used": ["small fixes should land alone"],
        "underdeveloped": ["testing strategy"],
        "open_threads": ["how much scope belongs in one PR"],
        "trajectory": "moving toward smaller, more isolated changes",
    }
    prompt = _facts_prompt(identity_state=state, recent_posts=[])
    assert "small fixes should land alone" in prompt
    assert "scope drift deserves its own commit" in prompt
    assert "moving toward smaller, more isolated changes" in prompt
    assert "none recorded yet" not in prompt


def test_fact_prompt_includes_real_recent_post_text_when_present():
    prompt = _facts_prompt(recent_posts=["Yesterday I shipped a small fix.", "Today I refactored a test."])
    assert "Yesterday I shipped a small fix." in prompt
    assert "Today I refactored a test." in prompt


def test_build_prompt_loads_identity_state_and_recent_posts_when_not_provided():
    fake_state = {**author_llm.identity_state_module.DEFAULT_IDENTITY_STATE,
                  "trajectory": "loaded from disk, not passed explicitly"}
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False), \
            mock.patch.object(author_llm.identity_state_module, "load_identity_state",
                               return_value=fake_state) as mock_load_state, \
            mock.patch.object(author_llm.identity_state_module, "load_recent_posts",
                               return_value=["a real recent post"]) as mock_load_posts:
        prompt = author_llm.build_prompt(SYNTHETIC_FACTS_BRIEF)
    mock_load_state.assert_called_once()
    mock_load_posts.assert_called_once()
    assert "loaded from disk, not passed explicitly" in prompt
    assert "a real recent post" in prompt


def test_idea_fallback_prompt_never_includes_identity_state_or_recent_posts():
    # idea_fallback mode isn't part of ADR-0059's fact-mode contract
    # (ADR-0044 remains normative there) — passing these inputs must
    # have zero effect on that branch.
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = author_llm.build_prompt(
            SAMPLE_IDEA_FALLBACK_DAILY_BRIEF,
            identity_state={"trajectory": "MUST_NOT_APPEAR"},
            recent_posts=["MUST_NOT_APPEAR_EITHER"],
        )
    assert "MUST_NOT_APPEAR" not in prompt
    assert "MUST_NOT_APPEAR_EITHER" not in prompt


def test_reasoning_validation_accepts_well_formed_object_and_rejects_missing_pieces():
    good = {
        "post": "text", "selected_cluster": "article-pipeline",
        "supporting_facts": ["article-pipeline:fact_01"],
        "reasoning": {
            "fact": "a", "tension": "b", "design_insight": "c",
            "personal_position": "d", "relevant_problem": "e",
        },
    }
    author_llm.validate_reasoning(good)  # must not raise

    missing_object = {k: v for k, v in good.items() if k != "reasoning"}
    try:
        author_llm.validate_reasoning(missing_object)
        raise AssertionError("expected AuthorLLMError for a response with no 'reasoning' object")
    except author_llm.AuthorLLMError as e:
        assert "reasoning" in str(e)

    for missing_field in author_llm.REASONING_REQUIRED_KEYS:
        broken = {**good, "reasoning": {k: v for k, v in good["reasoning"].items() if k != missing_field}}
        try:
            author_llm.validate_reasoning(broken)
            raise AssertionError(f"expected AuthorLLMError for a reasoning object missing {missing_field!r}")
        except author_llm.AuthorLLMError as e:
            assert missing_field in str(e), f"got: {e}"

    empty_field = {**good, "reasoning": {**good["reasoning"], "tension": "   "}}
    try:
        author_llm.validate_reasoning(empty_field)
        raise AssertionError("expected AuthorLLMError for a blank reasoning field")
    except author_llm.AuthorLLMError as e:
        assert "tension" in str(e)


def test_fact_prompt_says_no_reason_if_the_input_has_none():
    # ADR-0059 lifts the blanket reasoning ban but still forbids inventing a
    # reason absent from the data, explicitly including in PERSONAL POSITION.
    # Updated 2026-10-01 (ADR-0057 point 4 activation): a commit WITH its own
    # stated-reason/stated-effect fact is now an explicit exception -- see
    # test_fact_prompt_surfaces_stated_reason_and_effect_as_distinct_facts --
    # but SYNTHETIC_FACTS_BRIEF has no commit_evidence at all, so this test's
    # own commits still have no such fact and the prohibition still applies
    # to them in full.
    prompt = _facts_prompt()
    assert (
        "If a commit has no stated-reason/stated-effect fact, do "
        "not invent a reason or consequence for it — not even in the PERSONAL "
        "POSITION step below"
        in prompt
    )
    assert "ONLY source of facts" in prompt
    assert "Never invent a number" in prompt


def test_fact_prompt_states_the_evidence_boundary_explicitly():
    # Preserved unchanged from ADR-0057 (ADR-0059 Decision point 2): no
    # invented facts, and co-occurrence is never evidence of a causal or
    # design relationship.
    prompt = _facts_prompt()
    assert "Only use information present in the supplied data above" in prompt
    assert (
        "Temporal proximity or co-occurrence in the same batch is not "
        "evidence of a causal or design relationship"
    ) in prompt
    assert (
        "never invent a fact, user, reason, pain point, metric, or product "
        "state not present here"
    ) in prompt


# --- Why:/Effect: stated-reason evidence tier (ADR-0057 point 4 / ---------
# ADR-0059 activation, 2026-10-01) -------------------------------------------
# Replaces test_fact_prompt_stays_silent_about_commit_body_trailers, whose
# silence requirement this activation deliberately lifts: obsolete, not
# wrong, same treatment ADR-0059 Decision point 8 gave the old EMERGENT
# PROPERTY/INVERSION removal-assertion list.

SYNTHETIC_FACTS_BRIEF_WITH_EVIDENCE = {
    "mode": "fact",
    "date": "2026-10-01",
    "window": "1.day",
    "total_diffstat": 100,
    "files_touched": ["a.py"],
    "commit_messages": [
        "feat(author): wire Why:/Effect: evidence tier",
        "chore: unrelated tidy-up",
    ],
    "per_repo": [
        {
            "name": "article-pipeline",
            "commit_count": 2,
            "diffstat": 100,
            "files_touched": ["a.py"],
            "commit_messages": [
                "feat(author): wire Why:/Effect: evidence tier",
                "chore: unrelated tidy-up",
            ],
            "commit_evidence": [
                {
                    "sha": "1" * 40,
                    "subject": "feat(author): wire Why:/Effect: evidence tier",
                    "why": "ADR-0057 point 4 judged the trailer history sufficient",
                    "effect": "fact-mode can now cite a stated reason for this commit",
                },
            ],
        },
    ],
    "decision_source": "heuristic",
}


def _facts_prompt_with_evidence():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        return " ".join(author_llm.build_prompt(
            SYNTHETIC_FACTS_BRIEF_WITH_EVIDENCE,
            identity_state=dict(author_llm.identity_state_module.DEFAULT_IDENTITY_STATE),
            recent_posts=[],
        ).split())


def test_fact_prompt_surfaces_stated_reason_and_effect_as_distinct_facts():
    prompt = _facts_prompt_with_evidence()
    assert author_llm.FACT_KIND_STATED_WHY in prompt
    assert author_llm.FACT_KIND_STATED_EFFECT in prompt
    assert "ADR-0057 point 4 judged the trailer history sufficient" in prompt
    assert "fact-mode can now cite a stated reason for this commit" in prompt
    # Only the one commit with real commit_evidence produced a fact of this
    # kind — the second commit (no entry in commit_evidence) must not have
    # fabricated one.
    assert prompt.count(f"({author_llm.FACT_KIND_STATED_WHY}):") == 1
    assert prompt.count(f"({author_llm.FACT_KIND_STATED_EFFECT}):") == 1
    assert "chore: unrelated tidy-up" in prompt


def test_fact_prompt_omits_stated_reason_kind_entirely_when_no_commit_has_one():
    # SYNTHETIC_FACTS_BRIEF's per_repo entries carry no commit_evidence key
    # at all -- the baseline, pre-activation shape. The kind's own name
    # still appears once, in the static "what the data does and does not
    # contain" explanation (always present, independent of this run's
    # data) -- but no actual FACT line of that kind is offered, since none
    # was built from a commit with no commit_evidence entry.
    prompt = _facts_prompt()
    assert prompt.count(f"({author_llm.FACT_KIND_STATED_WHY}):") == 0
    assert prompt.count(f"({author_llm.FACT_KIND_STATED_EFFECT}):") == 0


def test_fact_prompt_allows_stating_a_reason_only_for_the_commits_own_trailer():
    prompt = _facts_prompt()
    assert (
        "if a commit has its own stated-reason and/or stated-effect fact "
        "in this cluster, you may state it as that specific commit's own "
        "stated reason/effect"
    ) in prompt
    assert (
        "never borrow another commit's stated reason or effect for it, "
        "even a commit in the same cluster"
    ) in prompt


def test_fact_prompt_final_evidence_check_covers_stated_reason_grounding():
    prompt = _facts_prompt()
    assert (
        "A stated reason or effect for a specific commit is valid only if "
        "it is directly supported by that same commit's own "
        "stated-reason/stated-effect fact among the selected cluster's "
        "offered facts"
    ) in prompt
    assert (
        "never inferred from a bare commit subject, and never borrowed "
        "from a different commit's own trailer, even one in the same cluster"
    ) in prompt


def test_reasoning_step_text_is_not_added_to_the_idea_fallback_prompt():
    # ADR-0059's five-step reasoning contract (fact-mode only) must not leak
    # into idea_fallback, which stays on ADR-0044's Narrative Bridge.
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = " ".join(author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF).split())
    assert "DESIGN INSIGHT" not in prompt
    assert "RELEVANT PROBLEM" not in prompt
    assert "FINAL EVIDENCE CHECK" not in prompt


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


_GOOD_REASONING = {
    "fact": "a", "tension": "b", "design_insight": "c",
    "personal_position": "d", "relevant_problem": "e",
}


def test_fact_response_requires_post_cluster_and_reasoning_keys():
    assert author_llm.FACT_REQUIRED_KEYS == {
        "post", "selected_cluster", "supporting_facts", "reasoning", "automation_only_day",
    }
    author_llm.validate_structured_response(
        {"automation_only_day": False,
         "post": "I pushed 3 commits to article-pipeline.",
         "selected_cluster": "article-pipeline",
         "supporting_facts": ["article-pipeline:fact_01"],
         "reasoning": dict(_GOOD_REASONING)},
        "fact", SYNTHETIC_FACTS_BRIEF,
    )  # must not raise
    for missing in ("selected_cluster", "supporting_facts", "reasoning", "automation_only_day"):
        full = {"automation_only_day": False, "post": "text", "selected_cluster": "article-pipeline",
                "supporting_facts": ["article-pipeline:fact_01"],
                "reasoning": dict(_GOOD_REASONING)}
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
    # A well-formed 'reasoning' object by default: these tests target
    # selected_cluster/supporting_facts citation logic, not reasoning shape
    # (covered separately by test_reasoning_validation_accepts_well_formed_
    # object_and_rejects_missing_pieces).
    return {"automation_only_day": False, "post": "I pushed commits.", "selected_cluster": post_cluster,
            "supporting_facts": facts, "reasoning": dict(_GOOD_REASONING)}


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
           "supporting_facts": ["article-pipeline:fact_01"], "reasoning": dict(_GOOD_REASONING),
           "automation_only_day": False}
    for mode in ("fact", "idea_fallback"):
        try:
            author_llm.validate_structured_response(bad, mode)
            raise AssertionError(f"expected AuthorLLMError in mode={mode}")
        except author_llm.AuthorLLMError as e:
            assert "greeting" in str(e)


# --- Fact-mode published-post voice: no third-person self-reference ---------
# The gate under test checks the synthesized `post` string itself — the
# actual output — not whether the prompt asks for first person.

THIRD_PERSON_SELF_REFERENCE_POSTS = (
    "The author treats scope correction as part of shipping. I changed three things today.",
    "I shipped three commits today. This is what the owner's pipeline needed.",
    "I bumped a header today.\n\nThe author's habit is to fail loudly before publication.",
    "This author prefers checks that fail before anything is published.",
    "I bumped a header today. Then the author noted that the old one had expired.",
)

FIRST_PERSON_POST_WITH_POSITION = (
    "I merged three commits into article-pipeline today. One made the Publication "
    "Registry accept a caller-supplied content_id.\n\n"
    "Both changes leave a check running before anything is published, never after. "
    "I prefer a gate that fails before publication over a review that happens after it. "
    "Today's work strengthens that preference for me.\n\n"
    "Where would you place the check in your own pipeline?"
)

# Legitimate wording that merely resembles the self-reference forms or the
# FINAL EVIDENCE CHECK's "nobody"/"the team" wording — a different concern,
# which this gate must not conflate with third-person self-reference.
NON_SELF_REFERENCE_POSTS = (
    "I noticed that nobody on the call mentioned the expired header.",
    "The team reviewed the change before I merged it.",
    "The Author component now reads the cluster IDs from the brief.",
    "I moved the Owner Verdict Capture step ahead of the registry write.",
)


def test_fact_post_voice_rejects_third_person_self_reference():
    for post in THIRD_PERSON_SELF_REFERENCE_POSTS:
        try:
            author_llm.check_fact_post_voice(post)
            raise AssertionError(f"expected AuthorLLMError for {post!r}")
        except author_llm.AuthorLLMError as e:
            assert "third-person self-reference" in str(e), f"got: {e}"


def test_fact_post_voice_accepts_first_person_posts():
    author_llm.check_fact_post_voice(FIRST_PERSON_POST_WITH_POSITION)  # must not raise
    author_llm.check_fact_post_voice(PLAIN_FACTS_ONLY_POST)  # must not raise


def test_fact_post_voice_does_not_flag_wording_that_is_not_self_reference():
    for post in NON_SELF_REFERENCE_POSTS:
        author_llm.check_fact_post_voice(post)  # must not raise


def test_fact_mode_validation_rejects_a_post_with_third_person_self_reference():
    for post in THIRD_PERSON_SELF_REFERENCE_POSTS:
        response = _cited("article-pipeline", ["article-pipeline:fact_01"])
        response["post"] = post
        _assert_rejected(response, SYNTHETIC_FACTS_BRIEF, "third-person self-reference")


def test_fact_mode_validation_accepts_a_first_person_post():
    response = _cited("article-pipeline", ["article-pipeline:fact_01"])
    response["post"] = FIRST_PERSON_POST_WITH_POSITION
    author_llm.validate_structured_response(response, "fact", SYNTHETIC_FACTS_BRIEF)  # must not raise


def test_third_person_reasoning_fields_do_not_trip_the_post_voice_gate():
    # `reasoning` is for the owner's own review and is not published; only
    # the `post` field is checked for voice.
    response = _cited("article-pipeline", ["article-pipeline:fact_01"])
    response["post"] = FIRST_PERSON_POST_WITH_POSITION
    response["reasoning"]["design_insight"] = "The author treats scope correction as part of shipping."
    author_llm.validate_structured_response(response, "fact", SYNTHETIC_FACTS_BRIEF)  # must not raise


def test_automation_only_day_response_is_unaffected_by_the_voice_gate():
    author_llm.validate_structured_response(
        dict(_GOOD_AUTOMATION_ONLY_RESPONSE), "fact", SYNTHETIC_FACTS_BRIEF
    )  # must not raise


def test_idea_fallback_validation_is_not_subject_to_the_fact_mode_voice_gate():
    # ADR-0044 still governs idea_fallback; the fact-mode voice gate must
    # not reach it.
    author_llm.validate_structured_response(
        {"post": "The author sees a reimagined use for this product.",
         "fact_or_product": "Collector", "emergent_property": "x", "evidence_to_collect": "y"},
        "idea_fallback",
    )  # must not raise


def _prompt_segment(prompt, start_marker, end_marker):
    start = prompt.index(start_marker)
    return prompt[start:prompt.index(end_marker, start)]


def test_fact_prompt_reasoning_steps_do_not_use_the_author_or_owner_as_subject():
    # Secondary prompt-shape check, NOT proof of the fix (the output gate
    # above is): FACT, DESIGN INSIGHT and PERSONAL POSITION must not
    # model third-person self-reference for the post.
    prompt = _facts_prompt()
    steps = _prompt_segment(prompt, "1. FACT", "5. RELEVANT PROBLEM")
    # DESIGN INSIGHT names the forbidden forms once, in a prohibition; that
    # one quoted mention is the only allowed occurrence.
    prohibition = 'never "the author" or "the owner"'
    assert steps.count(prohibition) == 1
    steps = steps.replace(prohibition, "")
    for forbidden in ("the author", "the owner", "The author", "The owner"):
        assert forbidden not in steps, f"reasoning steps still use {forbidden!r} as a subject"


def test_fact_prompt_design_insight_analyzes_the_work_and_hands_a_preference_to_the_first_person_position():
    prompt = _facts_prompt()
    design_insight = _prompt_segment(prompt, "3. DESIGN INSIGHT", "4. PERSONAL POSITION")
    assert "the work" in design_insight and "the engineering choice" in design_insight
    assert "engineering preference or design value" in design_insight
    assert "first-person position" in design_insight
    # Pinned instructions that must survive the rewording.
    assert "The insight must preserve the exact object of the tension" in design_insight
    assert "Specificity test" in design_insight


def test_fact_prompt_personal_position_stays_the_explicit_first_person_bridge():
    prompt = _facts_prompt()
    position = _prompt_segment(prompt, "4. PERSONAL POSITION", "5. RELEVANT PROBLEM")
    assert "present-tense first-person position" in position
    assert "(I/my)" in position
    assert "engineering preference or design value" in position
    assert "The position must still originate from today's tension" in position


def test_fact_prompt_states_first_person_as_a_hard_contract_at_post_synthesis():
    prompt = _facts_prompt()
    synthesis = _prompt_segment(prompt, 'Then write "post"', "FINAL EVIDENCE CHECK")
    assert "first person throughout" in synthesis
    assert 'never "the author" or "the owner"' in synthesis


def test_fact_prompt_keeps_voice_check_separate_from_evidence_check():
    prompt = _facts_prompt()
    assert prompt.index("FINAL EVIDENCE CHECK") < prompt.index("FINAL VOICE CHECK")
    evidence_check = _prompt_segment(prompt, "FINAL EVIDENCE CHECK", "FINAL VOICE CHECK")
    # The evidence check keeps its own scope; voice is not folded into it.
    assert "first-person" not in evidence_check and "first person" not in evidence_check
    voice_check = _prompt_segment(prompt, "FINAL VOICE CHECK", "Numbers:")
    assert "first-person position" in voice_check


def test_idea_fallback_prompt_has_no_fact_mode_voice_contract_text():
    with mock.patch.object(author_llm, "_check_repo_visibility", return_value=False):
        prompt = " ".join(author_llm.build_prompt(SAMPLE_IDEA_FALLBACK_DAILY_BRIEF).split())
    assert "FINAL VOICE CHECK" not in prompt
    assert "first person throughout" not in prompt


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
    incomplete_payload = {"post": "some text"}  # missing selected_cluster/supporting_facts/reasoning
    try:
        author_llm.validate_structured_response(incomplete_payload, "fact")
        raise AssertionError("expected AuthorLLMError for a response missing required keys")
    except author_llm.AuthorLLMError as e:
        assert "selected_cluster" in str(e), f"error should name the missing key(s), got: {e}"


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


def _call_model_with_raw_text(raw_text: str):
    """Runs call_model() against a mocked Anthropic client whose text
    block carries `raw_text` verbatim (no json.dumps), so a test can
    feed it deliberately malformed or unescaped JSON."""
    with mock.patch.object(author_llm, "_get_api_key", return_value="fake-key"), \
            mock.patch("daily_linkedin_author.anthropic.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        content_block = mock.Mock()
        content_block.type = "text"
        content_block.text = raw_text
        fake_response = mock.Mock()
        fake_response.content = [content_block]
        mock_client.messages.create.return_value = fake_response
        return author_llm.call_model("irrelevant prompt")


_RAW_NEWLINE_PAYLOAD = {
    "automation_only_day": False,
    "post": "First paragraph of a synthetic post.\n\nSecond paragraph,\twith a tab.\n\nThird paragraph.",
    "selected_cluster": "article-pipeline",
    "supporting_facts": ["article-pipeline:fact_01"],
    "reasoning": {
        "fact": "A synthetic fact.\nOn two lines.",
        "tension": "A synthetic tension.",
        "design_insight": "A synthetic design insight.",
        "personal_position": "A synthetic personal position.",
        "relevant_problem": "A synthetic relevant problem.",
    },
}


def _raw_control_character_response_text() -> str:
    """The failure shape of the 2026-10-01 run: a valid JSON object whose
    string values carry literal line breaks/tabs instead of the escaped
    `\\n`/`\\t` sequences the JSON grammar requires."""
    import json as _json
    escaped = _json.dumps(_RAW_NEWLINE_PAYLOAD)
    return escaped.replace("\\n", "\n").replace("\\t", "\t")


def test_call_model_tolerates_raw_control_characters_in_string_values():
    import json as _json
    raw_text = _raw_control_character_response_text()
    # Precondition: this really is the failure shape strict parsing rejects.
    try:
        _json.loads(raw_text)
        raise AssertionError("fixture must be rejected by strict json.loads")
    except _json.JSONDecodeError as e:
        assert "control character" in str(e)
    assert "\n" in raw_text and "\t" in raw_text

    response = _call_model_with_raw_text(raw_text)

    # Same structured result as the properly escaped response.
    assert response == _RAW_NEWLINE_PAYLOAD
    assert response == _json.loads(_json.dumps(_RAW_NEWLINE_PAYLOAD))
    # Paragraph breaks in the post text are preserved, not collapsed.
    assert response["post"].count("\n\n") == 2
    assert response["post"].split("\n\n")[1].startswith("Second paragraph")
    # Nested string values are covered too.
    assert response["reasoning"]["fact"] == "A synthetic fact.\nOn two lines."
    author_llm.validate_structured_response(
        response, "fact", SAMPLE_FACT_DAILY_BRIEF
    )  # must not raise


def test_call_model_tolerates_raw_control_characters_inside_markdown_fence():
    raw_text = "```json\n" + _raw_control_character_response_text() + "\n```"
    assert _call_model_with_raw_text(raw_text) == _RAW_NEWLINE_PAYLOAD


def test_other_invalid_json_still_raises_author_llm_error_despite_tolerance():
    # Tolerating raw control characters must not loosen anything else:
    # every one of these is still rejected, including ones that also
    # carry raw line breaks.
    cases = {
        "truncated object": '{"post": "cut off',
        "trailing comma": '{"post": "x",}',
        "single-quoted keys": "{'post': 'x'}",
        "unescaped inner quote": '{"post": "she said "hi" to me"}',
        "missing closing brace": '{"post": "a\n\nb"',
        "bare prose": "this is not json at all",
        "empty response": "",
        "unquoted key with raw newline": '{post: "a\n\nb"}',
    }
    for label, raw_text in cases.items():
        try:
            _call_model_with_raw_text(raw_text)
            raise AssertionError(f"expected AuthorLLMError for {label}")
        except author_llm.AuthorLLMError as e:
            assert "not valid JSON" in str(e), f"{label}: got {e}"


def test_raw_control_characters_do_not_bypass_required_key_validation():
    import json as _json
    incomplete = {"post": "First paragraph.\n\nSecond paragraph."}  # no selected_cluster/reasoning/...
    raw_text = _json.dumps(incomplete).replace("\\n", "\n")
    response = _call_model_with_raw_text(raw_text)
    assert response == incomplete
    try:
        author_llm.validate_structured_response(response, "fact")
        raise AssertionError("expected AuthorLLMError for a response missing required keys")
    except author_llm.AuthorLLMError as e:
        assert "selected_cluster" in str(e), f"error should name the missing key(s), got: {e}"


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
        test_fact_prompt_has_five_step_reasoning_shape_in_order,
        test_fact_prompt_each_step_carries_its_own_defining_instruction,
        test_fact_prompt_final_evidence_check_content_is_present,
        test_fact_prompt_includes_automation_only_day_guard_prose,
        test_fact_prompt_output_format_documents_automation_only_day_field,
        test_idea_fallback_prompt_never_mentions_automation_only_day,
        test_automation_only_day_response_well_formed_passes_validation,
        test_automation_only_day_response_rejects_non_empty_post,
        test_automation_only_day_response_rejects_non_empty_supporting_facts,
        test_automation_only_day_response_rejects_cluster_not_offered,
        test_automation_only_day_response_rejects_blank_reasoning_fact,
        test_automation_only_day_response_rejects_non_empty_other_reasoning_fields,
        test_automation_only_day_true_is_distinguished_from_false_by_type,
        test_fact_prompt_drops_adr_0057_facts_only_prohibition_language,
        test_fact_prompt_says_none_recorded_yet_when_no_history_exists,
        test_fact_prompt_includes_identity_state_positions_and_trajectory_when_present,
        test_fact_prompt_includes_real_recent_post_text_when_present,
        test_build_prompt_loads_identity_state_and_recent_posts_when_not_provided,
        test_idea_fallback_prompt_never_includes_identity_state_or_recent_posts,
        test_reasoning_validation_accepts_well_formed_object_and_rejects_missing_pieces,
        test_fact_prompt_says_no_reason_if_the_input_has_none,
        test_fact_prompt_states_the_evidence_boundary_explicitly,
        test_fact_prompt_surfaces_stated_reason_and_effect_as_distinct_facts,
        test_fact_prompt_omits_stated_reason_kind_entirely_when_no_commit_has_one,
        test_fact_prompt_allows_stating_a_reason_only_for_the_commits_own_trailer,
        test_fact_prompt_final_evidence_check_covers_stated_reason_grounding,
        test_reasoning_step_text_is_not_added_to_the_idea_fallback_prompt,
        test_fact_prompt_forbids_naming_adr_numbers,
        test_fact_prompt_keeps_the_l2_public_link_mechanism,
        test_fact_response_requires_post_cluster_and_reasoning_keys,
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
        test_fact_post_voice_rejects_third_person_self_reference,
        test_fact_post_voice_accepts_first_person_posts,
        test_fact_post_voice_does_not_flag_wording_that_is_not_self_reference,
        test_fact_mode_validation_rejects_a_post_with_third_person_self_reference,
        test_fact_mode_validation_accepts_a_first_person_post,
        test_third_person_reasoning_fields_do_not_trip_the_post_voice_gate,
        test_automation_only_day_response_is_unaffected_by_the_voice_gate,
        test_idea_fallback_validation_is_not_subject_to_the_fact_mode_voice_gate,
        test_fact_prompt_reasoning_steps_do_not_use_the_author_or_owner_as_subject,
        test_fact_prompt_design_insight_analyzes_the_work_and_hands_a_preference_to_the_first_person_position,
        test_fact_prompt_personal_position_stays_the_explicit_first_person_bridge,
        test_fact_prompt_states_first_person_as_a_hard_contract_at_post_synthesis,
        test_fact_prompt_keeps_voice_check_separate_from_evidence_check,
        test_idea_fallback_prompt_has_no_fact_mode_voice_contract_text,
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
        test_call_model_tolerates_raw_control_characters_in_string_values,
        test_call_model_tolerates_raw_control_characters_inside_markdown_fence,
        test_other_invalid_json_still_raises_author_llm_error_despite_tolerance,
        test_raw_control_characters_do_not_bypass_required_key_validation,
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
