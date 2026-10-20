import pytest

from habr_draft.budget import (
    BudgetGuard, BudgetRefused, estimate_call_cost_usd, input_tokens_estimate,
)
from habr_draft.llm import HabrLLM, LlmExecutionError, LlmRequest
from habr_draft.testsupport import make_config


def test_estimate_divides_by_one_million():
    # 1000 input "tokens" (1000 ASCII bytes) at 2 USD/Mtok, 0 output, no retries:
    # 1000 * 2 / 1_000_000 = 0.002
    cost = estimate_call_cost_usd(["a" * 1000], max_tokens=0, max_retries=0,
                                  price_in_per_mtok=2.0, price_out_per_mtok=10.0)
    assert cost == pytest.approx(0.002)
    # output side: 500 tokens at 10 USD/Mtok = 0.005
    cost = estimate_call_cost_usd([], max_tokens=500, max_retries=0,
                                  price_in_per_mtok=2.0, price_out_per_mtok=10.0)
    assert cost == pytest.approx(0.005)


def test_estimate_applies_retry_multiplier():
    base = estimate_call_cost_usd(["a" * 1000], max_tokens=500, max_retries=0,
                                  price_in_per_mtok=2.0, price_out_per_mtok=10.0)
    with_retries = estimate_call_cost_usd(["a" * 1000], max_tokens=500, max_retries=2,
                                          price_in_per_mtok=2.0, price_out_per_mtok=10.0)
    assert with_retries == pytest.approx(base * 3)


def test_estimate_counts_utf8_bytes_not_characters():
    assert input_tokens_estimate(["привет"]) == len("привет".encode("utf-8")) == 12


def test_request_estimate_includes_every_billable_text_field():
    request = LlmRequest(system="s" * 10, task="t" * 20, rubric="r" * 30,
                         reference="f" * 40, extra=("e" * 50, "x" * 60))
    assert input_tokens_estimate(request.billable_texts()) == 10 + 20 + 30 + 40 + 50 + 60
    # and each of those fields really is sent: system separately, the rest in the user message
    message = request.user_message()
    for part in ("t" * 20, "r" * 30, "f" * 40, "e" * 50, "x" * 60):
        assert part in message
    assert "s" * 10 not in message  # system travels in the system field


def test_each_field_changes_the_estimate():
    base = LlmRequest(system="", task="t")
    for field_name in ("system", "rubric", "reference"):
        bigger = LlmRequest(**{**{"system": "", "task": "t"}, field_name: "z" * 100})
        assert input_tokens_estimate(bigger.billable_texts()) == 101, field_name
    bigger = LlmRequest(system="", task="t", extra=("z" * 100,))
    assert input_tokens_estimate(bigger.billable_texts()) == 101
    assert input_tokens_estimate(base.billable_texts()) == 1


def test_guard_refuses_when_estimate_exceeds_remaining_budget():
    guard = BudgetGuard(limit_usd=0.001, price_in_per_mtok=2.0, price_out_per_mtok=10.0, max_retries=2)
    with pytest.raises(BudgetRefused):
        guard.check(["a" * 10000], max_tokens=1000)


def test_llm_does_not_call_the_model_when_refused():
    calls = []

    def caller(*args, **kwargs):  # pragma: no cover - must never run
        calls.append(1)
        return {}

    guard = BudgetGuard(limit_usd=0.0001, price_in_per_mtok=2.0, price_out_per_mtok=10.0, max_retries=2)
    llm = HabrLLM(make_config(), guard, caller=caller)
    with pytest.raises(LlmExecutionError) as caught:
        llm.ask(LlmRequest(system="s", task="t" * 5000), max_tokens=1000, purpose="generation")
    assert caught.value.kind == "budget_limit"
    assert calls == []


def test_guard_reports_best_effort_not_a_ceiling():
    guard = BudgetGuard(limit_usd=1.0, price_in_per_mtok=2.0, price_out_per_mtok=10.0, max_retries=2)
    report = guard.report()
    assert report["guard"] == "best_effort"
    assert "not a guaranteed maximum" in report["note"]


def test_guard_decrements_by_reported_usage():
    guard = BudgetGuard(limit_usd=1.0, price_in_per_mtok=2.0, price_out_per_mtok=10.0, max_retries=2)
    guard.record(0.0, input_tokens=1_000_000, output_tokens=100_000)
    assert guard.spent_usd == pytest.approx(2.0 + 1.0)
