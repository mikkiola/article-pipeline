"""Habr draft acceptance/runtime configuration (SPEC.md M9 requirement 50).

Every value the owner has not set is `null` and has no default: a check or a
paid call that needs it cannot execute. Nothing here invents a number. The
two prices are the owner's own figures (message of 2026-10-15).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PACKAGE_DIR / "acceptance_config.json"
RUBRIC_PATH = PACKAGE_DIR / "rubric_infostyle.md"


class ARules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_paragraph_chars: int | None = None
    max_code_block_lines: int | None = None
    # Habr's spoiler markup as an [open, close] pair of literal markers.
    # Unset until verified against Habr's editor; never assumed.
    spoiler_markup: list[str] | None = None


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_run_spend_usd: float | None = None
    max_fragment_chars_per_attempt: int | None = None
    max_tokens_generation: int | None = None
    max_tokens_judge: int | None = None
    price_in_per_mtok: float | None = None
    price_out_per_mtok: float | None = None


class AllowListEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo: str
    branch: str
    content_safety_checked: bool = False
    authorship_checked: bool = False


class HabrConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paid_calls_enabled: bool = False
    model: str
    api_key_env: str
    q_threshold: float | None = None
    a_rules: ARules = ARules()
    budget: Budget = Budget()
    allow_list: list[AllowListEntry] = []
    owner_identities: list[dict[str, str]] = []
    owner_authorization: dict[str, Any] | None = None
    calibration_approval: dict[str, Any] | None = None

    def allowed(self, repo: str, branch: str | None) -> AllowListEntry | None:
        for entry in self.allow_list:
            if entry.repo == repo and entry.branch == branch:
                return entry
        return None


def load_config(path: Path = CONFIG_PATH) -> HabrConfig:
    return HabrConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def missing_for_paid_calls(config: HabrConfig) -> list[str]:
    """Names of values a paid call needs and the owner has not set."""
    missing: list[str] = []
    if not config.paid_calls_enabled:
        missing.append("paid_calls_enabled")
    b = config.budget
    for name in (
        "max_run_spend_usd",
        "max_fragment_chars_per_attempt",
        "max_tokens_generation",
        "max_tokens_judge",
        "price_in_per_mtok",
        "price_out_per_mtok",
    ):
        if getattr(b, name) is None:
            missing.append(f"budget.{name}")
    return missing


def missing_for_selection(config: HabrConfig) -> list[str]:
    """Values without which candidate selection is meaningless. With none of
    these set, "no candidate qualified" would be a consequence of unset
    configuration, not an observation about the day's data, so a run must
    stop as missing configuration before it looks at any candidate.

    A repository that is individually uncleared is NOT missing configuration:
    it is excluded and recorded (stage 1, `source_not_cleared`)."""
    missing: list[str] = []
    if not any(e.content_safety_checked and e.authorship_checked for e in config.allow_list):
        missing.append("allow_list.cleared_repository")
    if not config.owner_identities:
        missing.append("owner_identities")
    return missing


def missing_for_production(config: HabrConfig) -> list[str]:
    """Production mode needs everything a paid call needs, plus every
    acceptance threshold and the authorizations."""
    missing = missing_for_paid_calls(config) + missing_for_selection(config)
    if config.q_threshold is None:
        missing.append("q_threshold")
    for name in ("max_paragraph_chars", "max_code_block_lines", "spoiler_markup"):
        if getattr(config.a_rules, name) is None:
            missing.append(f"a_rules.{name}")
    if config.owner_authorization is None:
        missing.append("owner_authorization")
    return missing


def missing_for_calibration(config: HabrConfig) -> list[str]:
    """Calibration needs the paid-call values and the owner's separate
    approval of the paid call and its budget; thresholds stay unset."""
    missing = missing_for_paid_calls(config) + missing_for_selection(config)
    if config.calibration_approval is None:
        missing.append("calibration_approval")
    return missing
