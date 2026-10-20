"""Pre-call budget guard (best-effort, not an absolute spend ceiling).

C_est = (1 + max_retries) * (input_tokens_estimate * price_in
                              + max_tokens * price_out) / 1_000_000

Prices are per million tokens. `input_tokens_estimate` is the UTF-8 byte count
of ALL billable input text of the request (system instructions, messages,
rubric text, reference text and any other textual field). It is a proxy for
the token count, not a tokenizer measurement and not a proven upper bound on
billed usage. Billing of retried or failed requests is not established, so the
configured limit is a best-effort guard, never a guaranteed maximum.
"""

from __future__ import annotations

from dataclasses import dataclass, field

GUARD_KIND = "best_effort"


class BudgetRefused(RuntimeError):
    """The estimated cost of the next call does not fit the remaining budget."""


def input_tokens_estimate(texts: list[str]) -> int:
    return sum(len(text.encode("utf-8")) for text in texts if text)


def estimate_call_cost_usd(
    texts: list[str],
    *,
    max_tokens: int,
    max_retries: int,
    price_in_per_mtok: float,
    price_out_per_mtok: float,
) -> float:
    tokens_in = input_tokens_estimate(texts)
    return (1 + max_retries) * (
        tokens_in * price_in_per_mtok + max_tokens * price_out_per_mtok
    ) / 1_000_000


@dataclass
class BudgetGuard:
    limit_usd: float
    price_in_per_mtok: float
    price_out_per_mtok: float
    max_retries: int
    spent_usd: float = 0.0
    calls: list[dict] = field(default_factory=list)

    @property
    def remaining_usd(self) -> float:
        return self.limit_usd - self.spent_usd

    def check(self, texts: list[str], max_tokens: int) -> float:
        """Raises BudgetRefused (and the caller must not call) when the
        estimate exceeds the remaining budget. Returns the estimate."""
        estimate = estimate_call_cost_usd(
            texts,
            max_tokens=max_tokens,
            max_retries=self.max_retries,
            price_in_per_mtok=self.price_in_per_mtok,
            price_out_per_mtok=self.price_out_per_mtok,
        )
        if estimate > self.remaining_usd:
            raise BudgetRefused(
                f"estimated worst-case cost {estimate:.6f} USD exceeds the remaining "
                f"budget {self.remaining_usd:.6f} USD; the call was not made"
            )
        return estimate

    def record(self, estimate: float, *, input_tokens: int | None, output_tokens: int | None) -> None:
        """Decrements the remaining budget by the cost of the usage the API
        reported. Failed or retried requests that reported nothing are not
        visible here (best-effort)."""
        actual = (
            (input_tokens or 0) * self.price_in_per_mtok
            + (output_tokens or 0) * self.price_out_per_mtok
        ) / 1_000_000
        self.spent_usd += actual
        self.calls.append(
            {"estimate_usd": estimate, "actual_usd": actual,
             "input_tokens": input_tokens, "output_tokens": output_tokens}
        )

    def report(self) -> dict:
        return {
            "limit_usd": self.limit_usd,
            "estimated_spend_usd": self.spent_usd,
            "guard": GUARD_KIND,
            "note": (
                "best-effort guard, not a guaranteed maximum: billing of retried or "
                "failed requests is not established"
            ),
            "calls": self.calls,
        }
