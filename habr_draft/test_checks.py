import pytest

from habr_draft import checks
from habr_draft.config import ARules
from habr_draft.testsupport import FRAGMENT_CONTENT, GOOD_BODY, good_fragment

RULES = ARules(max_paragraph_chars=2000, max_code_block_lines=5,
               spoiler_markup=["<spoiler>", "</spoiler>"])


def test_rules_pass_on_good_body():
    result = checks.check_habr_rules(GOOD_BODY, RULES)
    assert result.executed and result.passed, result.findings


def test_rules_flag_one_and_two_sentence_paragraphs():
    body = "Одно предложение здесь.\n\nДва предложения. Вот второе.\n\nТри. Предложения. Вот так."
    result = checks.check_habr_rules(body, RULES)
    flagged = [f for f in result.findings if f["rule"] == "habr_rule_3_short_paragraph"]
    assert [f["sentences"] for f in flagged] == [1, 2]
    assert result.passed is False


def test_code_and_headings_do_not_count_as_short_paragraphs():
    body = "# Заголовок\n\n```\nx = 1\n```\n\n- пункт\n"
    result = checks.check_habr_rules(body, RULES)
    assert not [f for f in result.findings if f["rule"] == "habr_rule_3_short_paragraph"]


def test_wall_of_text_needs_a_limit_and_is_flagged_above_it():
    long = ("Это предложение. " * 200).strip()
    result = checks.check_habr_rules(long, ARules(max_paragraph_chars=100, max_code_block_lines=5,
                                                  spoiler_markup=["<s>", "</s>"]))
    assert any(f["rule"] == "habr_rule_3_wall_of_text" for f in result.findings)


def test_long_code_block_outside_spoiler_is_flagged_inside_is_not():
    code = "\n".join(f"line{i}" for i in range(10))
    outside = f"Текст один. Текст два. Текст три.\n\n```\n{code}\n```\n"
    inside = f"Текст один. Текст два. Текст три.\n\n<spoiler>\n```\n{code}\n```\n</spoiler>\n"
    assert any(f["rule"] == "habr_rule_3_long_code_not_in_spoiler"
               for f in checks.check_habr_rules(outside, RULES).findings)
    assert not any(f["rule"] == "habr_rule_3_long_code_not_in_spoiler"
                   for f in checks.check_habr_rules(inside, RULES).findings)


def test_unset_values_make_rules_not_executable_but_keep_measurements():
    result = checks.check_habr_rules(GOOD_BODY, ARules())
    assert result.executed is False and result.passed is None
    assert set(result.missing_config) == {
        "a_rules.max_paragraph_chars", "a_rules.max_code_block_lines", "a_rules.spoiler_markup"}
    assert result.measurements["prose_paragraphs"] >= 1


def test_images_are_flagged_because_size_cannot_be_checked():
    result = checks.check_habr_rules(GOOD_BODY + "\n![x](http://e/p.png)\n", RULES)
    assert any(f["rule"] == "habr_rule_3_image_size_unverifiable" for f in result.findings)


def test_project_requirements_pass_with_russian_prose_and_verbatim_fragment():
    result = checks.check_project_requirements(GOOD_BODY, [good_fragment()])
    assert result.executed and result.passed, result.findings


def test_long_code_does_not_break_the_language_check():
    code = "\n".join(f"variable_name_{i} = some_function_call({i})" for i in range(60))
    body = f"Мы изменили код. Это важно. Вот результат.\n\n```\n{code}\n```\n"
    assert checks.check_project_requirements(body, [{"content": code}]).measurements["russian"] is True


def test_project_requirements_fail_without_verbatim_fragment():
    body = "Мы изменили код. Это важно. Вот результат.\n\n```\nsomething_else()\n```\n"
    result = checks.check_project_requirements(body, [good_fragment()])
    rules = {f["rule"] for f in result.findings}
    assert "no_verbatim_fragment" in rules and result.passed is False


def test_project_requirements_fail_for_english_prose():
    body = "We changed the code. It matters a lot. Here is the result.\n\n```\n" + FRAGMENT_CONTENT + "\n```\n"
    result = checks.check_project_requirements(body, [good_fragment()])
    assert any(f["rule"] == "output_not_russian" for f in result.findings)


BRIEF = {"per_repo": [{"name": "article-pipeline", "commit_count": 1,
                       "commit_messages": ["feat: compute in build"], "commit_evidence": [],
                       "files_touched": ["src/build.py"]}]}
RESPONSE = {"selected_cluster": "article-pipeline", "supporting_facts": ["article-pipeline:fact_01"]}
IDS = {"article-pipeline:fact_01", "article-pipeline:fact_02", "article-pipeline:frag_01"}


def test_l1_passes_when_every_statement_has_supplied_ids():
    judge = {"statements": [{"text": "a", "evidence_ids": ["article-pipeline:frag_01"]}]}
    result = checks.evaluate_l1(RESPONSE, BRIEF, IDS, judge)
    assert result.executed and result.passed, result.findings


def test_l1_fails_on_unsupported_unknown_and_missing_evidence():
    judge = {"statements": [
        {"text": "a", "evidence_ids": ["UNSUPPORTED"]},
        {"text": "b", "evidence_ids": ["article-pipeline:fact_99"]},
        {"text": "c", "evidence_ids": []},
    ]}
    result = checks.evaluate_l1(RESPONSE, BRIEF, IDS, judge)
    rules = [f["rule"] for f in result.findings]
    assert result.passed is False
    assert {"statement_unsupported", "statement_cites_unknown_id", "statement_without_evidence"} <= set(rules)


def test_l1_fails_when_cited_fact_is_outside_the_cluster():
    bad = {"selected_cluster": "article-pipeline", "supporting_facts": ["article-pipeline:fact_77"]}
    judge = {"statements": [{"text": "a", "evidence_ids": ["article-pipeline:frag_01"]}]}
    result = checks.evaluate_l1(bad, BRIEF, IDS, judge)
    assert any(f["rule"] == "cited_facts_not_in_cluster" for f in result.findings)
    assert result.passed is False


def test_l1_not_executed_when_judge_returns_no_statements():
    result = checks.evaluate_l1(RESPONSE, BRIEF, IDS, {"statements": []})
    assert result.executed is False and result.error


def test_q_unset_threshold_records_score_but_cannot_decide():
    result = checks.evaluate_q({"score": 55, "findings": [{"criterion": "x", "severity": "minor"}]}, None)
    assert result.executed is False and result.passed is None
    assert result.score == 55 and result.missing_config == ["q_threshold"]
    assert result.error is None  # missing configuration is not a technical failure


def test_q_pass_and_fail_against_threshold():
    assert checks.evaluate_q({"score": 80, "findings": []}, 70).passed is True
    assert checks.evaluate_q({"score": 60, "findings": []}, 70).passed is False


@pytest.mark.parametrize("score", ["high", True, -1, 101, 80.5, float("nan"), float("inf")])
def test_q_malformed_judge_is_a_technical_failure(score):
    result = checks.evaluate_q({"score": score, "findings": []}, 70)
    assert result.executed is False and result.error
