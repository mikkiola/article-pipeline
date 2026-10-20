import pytest

from habr_draft import loop
from habr_draft.checks import CheckResult
from habr_draft.llm import LlmExecutionError


def ok(name="c"):
    return CheckResult(name, True, True)


def bad(name="c"):
    return CheckResult(name, True, False, [{"rule": "x"}])


def missing(name="q_infostyle"):
    return CheckResult(name, False, None, missing_config=["q_threshold"], score=50.0)


def broken(name="l1"):
    return CheckResult(name, False, None, error="judge failed")


def draft(text="b"):
    return loop.Draft("t", text, {"k": text})


class Script:
    def __init__(self, rounds):
        self.rounds = list(rounds)
        self.generated = 0
        self.revised = 0
        self.evaluated = 0

    def generate(self):
        self.generated += 1
        return draft(f"g{self.generated}")

    def revise(self, previous, failed):
        self.revised += 1
        return draft(f"r{self.revised}")

    def evaluate(self, d):
        self.evaluated += 1
        item = self.rounds.pop(0) if len(self.rounds) > 1 else self.rounds[0]
        if isinstance(item, BaseException):
            raise item
        return item


def run(script, mode="production", scan=lambda text: []):
    return loop.run_rounds(generate=script.generate, revise=script.revise,
                           evaluate=script.evaluate, scan=scan, mode=mode)


def test_passes_in_first_round():
    s = Script([[ok("a"), ok("b"), ok("c"), ok("d")]])
    r = run(s)
    assert r.terminal_outcome == loop.READY and len(r.attempts) == 1 and s.revised == 0


def test_correction_then_pass():
    s = Script([[bad("a"), ok("b"), ok("c"), ok("d")], [ok("a"), ok("b"), ok("c"), ok("d")]])
    r = run(s)
    assert r.terminal_outcome == loop.READY
    assert [a.verdict for a in r.attempts] == [loop.QUALITY_BLOCK, "pass"]
    assert s.revised == 1


def test_blocked_after_two_correction_cycles_and_all_attempts_kept():
    s = Script([[bad("a"), bad("b"), ok("c"), ok("d")],
                [bad("a"), ok("b"), ok("c"), ok("d")],
                [bad("a"), bad("b"), bad("c"), ok("d")]])
    r = run(s)
    assert r.terminal_outcome == loop.BLOCKED
    assert len(r.attempts) == 3 and s.revised == 2  # initial + 2 corrections, no more
    assert all(a.saved for a in r.attempts)
    # best = fewest failed mandatory checks (attempt 2 has one failure)
    assert r.best_attempt == 2


def test_best_attempt_tie_goes_to_latest():
    s = Script([[bad("a"), ok("b"), ok("c"), ok("d")]])
    r = run(s)
    assert r.terminal_outcome == loop.BLOCKED and r.best_attempt == 3


def test_system_failure_takes_precedence_over_content_failure_in_same_round():
    s = Script([[bad("a"), broken("l1"), ok("c"), ok("d")]])
    r = run(s)
    assert r.terminal_outcome == loop.SYSTEM_FAILURE and r.failure_kind == "execution_error"
    assert s.revised == 0  # no correction cycle consumed


def test_system_failure_is_never_converted_to_blocked():
    s = Script([[ok("a"), ok("b"), ok("c"), broken("q")]])
    r = run(s)
    assert r.terminal_outcome == loop.SYSTEM_FAILURE and r.terminal_outcome != loop.BLOCKED


def test_missing_configuration_is_system_failure_with_its_own_kind():
    s = Script([[ok("a"), ok("b"), ok("c"), missing()]])
    r = run(s)
    assert r.terminal_outcome == loop.SYSTEM_FAILURE
    assert r.failure_kind == "missing_configuration"
    assert "q_threshold" in r.reason
    assert r.attempts[0].checks[3].score == 50.0  # score still recorded


def test_llm_failure_during_evaluation_is_system_failure_with_its_kind():
    s = Script([LlmExecutionError("budget_limit", "q_judge: over budget")])
    r = run(s)
    assert r.terminal_outcome == loop.SYSTEM_FAILURE and r.failure_kind == "budget_limit"


def test_generation_failure_is_system_failure():
    class G(Script):
        def generate(self):
            raise LlmExecutionError("execution_error", "generation: model call failed")

    r = run(G([[ok()]]))
    assert r.terminal_outcome == loop.SYSTEM_FAILURE and r.attempts == []


def test_calibration_is_one_round_never_ready_and_never_corrects():
    s = Script([[bad("a"), ok("b"), ok("c"), missing()]])
    r = run(s, mode="calibration")
    assert r.terminal_outcome is None
    assert len(r.attempts) == 1 and s.revised == 0
    assert r.attempts[0].verdict == "recorded"


def test_calibration_never_ready_even_if_everything_passes():
    s = Script([[ok("a"), ok("b"), ok("c"), ok("d")]])
    r = run(s, mode="calibration")
    assert r.terminal_outcome is None and r.terminal_outcome != loop.READY


def test_calibration_technical_failure_is_system_failure():
    r = run(Script([[ok("a"), broken("l1"), ok("c"), ok("d")]]), mode="calibration")
    assert r.terminal_outcome == loop.SYSTEM_FAILURE


def test_secret_gate_discards_draft_and_runs_no_checks():
    s = Script([[ok("a"), ok("b"), ok("c"), ok("d")]])
    hits_for = {"g1": [{"pattern_id": "github-token", "count": 1}]}

    def scan(text):
        return hits_for["g1"] if '"g1"' in text else []

    r = run(s, scan=scan)
    first = r.attempts[0]
    assert first.draft is None and not first.saved and first.checks == []
    assert first.verdict == loop.QUALITY_BLOCK
    assert s.evaluated == 1  # only the revised draft was evaluated
    assert r.terminal_outcome == loop.READY


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        run(Script([[ok()]]), mode="staging")
