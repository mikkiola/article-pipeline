"""The single door through which the Habr draft path makes paid model calls.

Every call: (1) is refused before it is made when its worst-case estimate does
not fit the remaining budget (budget.py), (2) goes through the existing
`author.daily_linkedin_author.call_model` with the Habr model, token limit and
API-key variable, and (3) never lets the model's raw response text escape in an
exception message or a log line: `call_model` puts the raw response in its
error text, so every failure is reduced to the exception class name before it
leaves this module.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "author"))

from habr_draft.budget import BudgetGuard, BudgetRefused  # noqa: E402
from habr_draft.config import HabrConfig  # noqa: E402


class LlmExecutionError(RuntimeError):
    """A model call could not be completed. `kind` is the SYSTEM_FAILURE
    failure_kind: `execution_error` or `budget_limit`. The message never
    contains model output."""

    def __init__(self, kind: str, reason: str):
        super().__init__(reason)
        self.kind = kind
        self.reason = reason


@dataclass(frozen=True)
class LlmRequest:
    """All billable text of one request, kept as separate fields so the
    budget estimate provably covers every one of them."""

    system: str
    task: str
    rubric: str = ""
    reference: str = ""
    extra: tuple[str, ...] = ()

    def billable_texts(self) -> list[str]:
        return [self.system, self.task, self.rubric, self.reference, *self.extra]

    def user_message(self) -> str:
        parts = [self.task, self.rubric, self.reference, *self.extra]
        return "\n\n".join(part for part in parts if part)


def default_max_retries() -> int:
    import anthropic

    return int(getattr(anthropic, "DEFAULT_MAX_RETRIES", 2))


def _default_caller() -> Callable[..., dict]:
    import daily_linkedin_author

    return daily_linkedin_author.call_model


class HabrLLM:
    def __init__(self, config: HabrConfig, guard: BudgetGuard, caller: Callable[..., dict] | None = None):
        self._config = config
        self._guard = guard
        self._caller = caller

    def ask(self, request: LlmRequest, *, max_tokens: int, purpose: str) -> dict:
        try:
            estimate = self._guard.check(request.billable_texts(), max_tokens)
        except BudgetRefused as refused:
            reason = f"{purpose}: {refused}"
            raise LlmExecutionError("budget_limit", reason) from None

        caller = self._caller or _default_caller()
        usage: dict = {}
        error_class: str | None = None
        result: dict | None = None
        try:
            result = caller(
                request.user_message(),
                model=self._config.model,
                max_tokens=max_tokens,
                api_key_env=self._config.api_key_env,
                system=request.system or None,
                usage_sink=usage,
            )
        except Exception as error:  # noqa: BLE001 - reduced to its class name below
            error_class = type(error).__name__
        if error_class is not None:
            raise LlmExecutionError(
                "execution_error",
                f"{purpose}: model call failed ({error_class}); response text suppressed",
            )
        self._guard.record(
            estimate,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )
        if not isinstance(result, dict):
            raise LlmExecutionError(
                "execution_error", f"{purpose}: model response was not a JSON object"
            )
        return result
