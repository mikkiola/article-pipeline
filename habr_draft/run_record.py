"""Immutable attempt files and the run outcome record
(SPEC.md M9 requirements 48-49).

Every file is created with exclusive-create semantics: a name collision raises
FileExistsError and nothing is ever overwritten (the pattern of
`strategy_layer/write_verdict.write_outputs`). The notification status is NOT
part of the record; it is logged by the workflow separately.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from habr_draft import secret_scan  # noqa: E402

OUTPUT_DIR_ENV = "HABR_DRAFT_OUTPUT_DIR"

# The only values `failure_kind` may take, and only inside SYSTEM_FAILURE:
#   missing_configuration  a required owner-set value is unset (not an outage)
#   execution_error        a mandatory step could not execute
#   budget_limit           the pre-call spend guard refused a call
#   input_validation       the run's input failed validation before selection
TERMINAL_OUTCOMES = ("INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW", "BLOCKED", "SYSTEM_FAILURE")

FAILURE_KINDS = ("missing_configuration", "execution_error", "budget_limit", "input_validation")

NOT_APPROVAL_STATEMENT = (
    "This outcome is not publication approval. It records only what the "
    "automated checks established about an internal draft."
)
READY_STATEMENT = (
    "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW means only that L1 (fact "
    "verification), the machine-checkable Habr rules, the project acceptance "
    "requirements and Q (infostyle) passed. Habr rule 4 (generated material) "
    "and rule 1 (self-promotion) are not established by any check, and neither "
    "are the topic and format requirements of Habr's rules beyond what (a) "
    "checks; those are the owner's editorial judgment. The draft is not to be "
    "represented as publication-ready for Habr unless the owner has "
    "independently created or substantially authored the final technical "
    "article, with any AI-generated material limited to what the current Habr "
    "rules permit."
)
CALIBRATION_STATEMENT = (
    "Calibration run: acceptance was not evaluated. terminal_outcome is null "
    "and calibration_result records that the check results, the Q score and "
    "the reference-text hash were recorded."
)
SECRET_SCAN_LIMIT_STATEMENT = (
    "The secret-pattern scan uses this repository's .gitleaks.toml rules plus a "
    "minimal set of well-known credential formats; it is not the full gitleaks "
    "default ruleset."
)
L1_LIMIT_STATEMENT = (
    "L1 verifies that cited fact ids exist in what the run supplied and that a "
    "judge mapped every statement to supplied ids; the judge's mapping is "
    "model-asserted and is not proof of semantic faithfulness."
)


def validate_outcome(terminal_outcome: str | None, failure_kind: str | None) -> None:
    """`failure_kind` belongs to SYSTEM_FAILURE and only to it; a run that
    ends as SYSTEM_FAILURE always names its kind."""
    if terminal_outcome is not None and terminal_outcome not in TERMINAL_OUTCOMES:
        raise ValueError("unknown terminal_outcome")
    if failure_kind is not None and failure_kind not in FAILURE_KINDS:
        raise ValueError(f"unknown failure_kind {failure_kind!r}")
    if failure_kind is not None and terminal_outcome != "SYSTEM_FAILURE":
        raise ValueError("failure_kind is only valid with terminal_outcome SYSTEM_FAILURE")
    if terminal_outcome == "SYSTEM_FAILURE" and failure_kind is None:
        raise ValueError("SYSTEM_FAILURE requires a failure_kind")


def build_report(terminal_outcome: str | None, mode: str, failure_kind: str | None) -> str:
    parts = [NOT_APPROVAL_STATEMENT]
    if mode == "calibration":
        parts.append(CALIBRATION_STATEMENT)
    if terminal_outcome == "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW":
        parts.append(READY_STATEMENT)
    if terminal_outcome == "SYSTEM_FAILURE" and failure_kind == "missing_configuration":
        parts.append(
            "A required configuration value is unset; this is a missing "
            "configuration, not a service outage, and not a quality failure."
        )
    if terminal_outcome == "SYSTEM_FAILURE" and failure_kind == "input_validation":
        parts.append(
            "The run's input failed validation before any topic was selected "
            "and before any model call; this is not a service outage and not "
            "a quality failure."
        )
    parts.append(L1_LIMIT_STATEMENT)
    parts.append(SECRET_SCAN_LIMIT_STATEMENT)
    return "\n".join(parts)


def output_dir_from_env() -> Path:
    value = os.environ.get(OUTPUT_DIR_ENV)
    if not value:
        raise RuntimeError(f"{OUTPUT_DIR_ENV} is not set")
    return Path(value)


def write_new(path: Path, content: str) -> str:
    """Exclusive create. Returns the sha256 of the written bytes."""
    data = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as handle:
        handle.write(data)
    return hashlib.sha256(data).hexdigest()


def write_attempt(directory: Path, number: int, title: str, body: str) -> dict:
    name = f"attempt_{number}.md"
    digest = write_new(directory / name, f"# {title}\n\n{body}\n")
    return {"name": name, "sha256": digest}


def _redact(obj, patterns):
    if isinstance(obj, str):
        return "[redacted: likely secret pattern]" if secret_scan.scan(obj, patterns) else obj
    if isinstance(obj, list):
        return [_redact(item, patterns) for item in obj]
    if isinstance(obj, dict):
        return {key: _redact(value, patterns) for key, value in obj.items()}
    return obj


def write_run_record(directory: Path, run_id: str, record: dict) -> dict:
    """Defence in depth: any string in the record that matches a secret
    pattern is replaced before the record is written."""
    validate_outcome(record.get("terminal_outcome"), record.get("failure_kind"))
    patterns = secret_scan.load_patterns()
    safe = _redact(record, patterns)
    name = f"run_{run_id}.json"
    digest = write_new(directory / name, json.dumps(safe, indent=2, ensure_ascii=False) + "\n")
    return {"name": name, "sha256": digest}
