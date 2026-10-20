"""The bounded revision loop and its outcome state machine
(SPEC.md M9 requirement 47; ADR-0071).

Pure orchestration over injected callables, so the whole state machine is
testable without a network or a model.

Production mode: at most 2 correction cycles after the initial draft (at most
3 rounds), all mandatory checks every round.
 - a check that cannot execute            -> SYSTEM_FAILURE (precedence over a
   content failure in the same round; consumes no correction cycle)
 - all four pass                          -> INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW
 - an executed check fails, cycles remain -> QUALITY_BLOCK, revise, re-check
 - an executed check fails, no cycle left -> BLOCKED

Calibration mode: exactly one round, no correction cycle, never READY. The
checks and the Q score are recorded; the terminal outcome is None
(acceptance not evaluated), or SYSTEM_FAILURE when a check could not run for a
technical reason.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from habr_draft.checks import CheckResult  # noqa: E402
from habr_draft.llm import LlmExecutionError  # noqa: E402

READY = "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW"
QUALITY_BLOCK = "QUALITY_BLOCK"
BLOCKED = "BLOCKED"
SYSTEM_FAILURE = "SYSTEM_FAILURE"

MAX_CORRECTIONS = 2


@dataclass
class Draft:
    title: str
    body: str
    response: dict


@dataclass
class Attempt:
    number: int
    verdict: str  # "pass" | QUALITY_BLOCK | SYSTEM_FAILURE | "recorded" (calibration)
    draft: Draft | None  # None when discarded by the secret gate
    checks: list[CheckResult] = field(default_factory=list)
    secret_hits: list[dict] = field(default_factory=list)

    @property
    def saved(self) -> bool:
        return self.draft is not None

    @property
    def failed_mandatory(self) -> int:
        return sum(1 for c in self.checks if c.passed is not True)


@dataclass
class LoopResult:
    mode: str
    attempts: list[Attempt]
    terminal_outcome: str | None
    failure_kind: str | None = None
    reason: str | None = None
    best_attempt: int | None = None


def _failed_findings(attempt: Attempt) -> list[dict]:
    failed = []
    if attempt.secret_hits:
        failed.append(
            {"check": "output_secret_gate",
             "findings": [{"rule": "likely_secret_pattern",
                           "patterns": [h["pattern_id"] for h in attempt.secret_hits]}]}
        )
    for check in attempt.checks:
        if check.passed is False:
            failed.append({"check": check.name, "findings": check.findings})
    return failed


def _best(attempts: list[Attempt]) -> int | None:
    saved = [a for a in attempts if a.saved and a.checks]
    if not saved:
        return None
    best = min(saved, key=lambda a: (a.failed_mandatory, -a.number))
    return best.number


def run_rounds(
    *,
    generate: Callable[[], Draft],
    revise: Callable[[Draft | None, list[dict]], Draft],
    evaluate: Callable[[Draft], list[CheckResult]],
    scan: Callable[[str], list[dict]],
    mode: str = "production",
    max_corrections: int = MAX_CORRECTIONS,
    on_attempt: Callable[[Attempt], None] | None = None,
) -> LoopResult:
    if mode not in ("production", "calibration"):
        raise ValueError(f"unknown mode {mode!r}")
    corrections_left = 0 if mode == "calibration" else max_corrections
    attempts: list[Attempt] = []
    previous: Attempt | None = None

    def finish(outcome, kind=None, reason=None) -> LoopResult:
        return LoopResult(mode, attempts, outcome, kind, reason, _best(attempts))

    while True:
        number = len(attempts) + 1
        try:
            if previous is None:
                draft = generate()
            else:
                draft = revise(previous.draft, _failed_findings(previous))
        except LlmExecutionError as error:
            return finish(SYSTEM_FAILURE, error.kind, error.reason)

        hits = scan(json.dumps(draft.response, ensure_ascii=False))
        if hits:
            # The text is neither persisted nor logged nor sent to a judge.
            attempt = Attempt(number, "recorded" if mode == "calibration" else QUALITY_BLOCK,
                              None, [], hits)
        else:
            try:
                results = evaluate(draft)
            except LlmExecutionError as error:
                attempts.append(Attempt(number, SYSTEM_FAILURE, draft, []))
                if on_attempt:
                    on_attempt(attempts[-1])
                return finish(SYSTEM_FAILURE, error.kind, error.reason)
            attempt = Attempt(number, "pass", draft, results)
            errors = [c for c in results if not c.executed and c.error]
            missing = [c for c in results if not c.executed and not c.error]
            if errors:
                attempt.verdict = SYSTEM_FAILURE
                attempts.append(attempt)
                if on_attempt:
                    on_attempt(attempt)
                return finish(SYSTEM_FAILURE, "execution_error",
                              "; ".join(f"{c.name}: {c.error}" for c in errors))
            if mode == "production" and missing:
                attempt.verdict = SYSTEM_FAILURE
                attempts.append(attempt)
                if on_attempt:
                    on_attempt(attempt)
                names = sorted({n for c in missing for n in c.missing_config})
                return finish(SYSTEM_FAILURE, "missing_configuration",
                              "required configuration unset: " + ", ".join(names))
            if mode == "calibration":
                attempt.verdict = "recorded"
            elif all(c.passed is True for c in results):
                attempt.verdict = "pass"
            else:
                attempt.verdict = QUALITY_BLOCK

        attempts.append(attempt)
        if on_attempt:
            on_attempt(attempt)

        if mode == "calibration":
            return finish(None)
        if attempt.verdict == "pass":
            return finish(READY)
        if corrections_left <= 0:
            return finish(BLOCKED, reason="correction limit exhausted without a round passing all checks")
        corrections_left -= 1
        previous = attempt
