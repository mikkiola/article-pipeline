"""Secret-pattern scan shared by input fragments and generated drafts.

Reuses the project's own `.gitleaks.toml` rules (parsed with the standard
library) plus a minimal set of well-known credential formats. This is NOT the
full gitleaks default ruleset (that needs the gitleaks binary); the limit is
stated in every run report.

A result never contains the matched text: only the pattern id and a count, so
nothing sensitive can be persisted or logged through a finding.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GITLEAKS_PATH = REPO_ROOT / ".gitleaks.toml"

BUILTIN_PATTERNS: dict[str, str] = {
    "github-token": r"gh[pousr]_[A-Za-z0-9]{36,}",
    "private-key-block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "aws-access-key-id": r"AKIA[0-9A-Z]{16}",
    "slack-token": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    "anthropic-api-key": r"sk-ant-[A-Za-z0-9_-]{20,}",
}


class SecretScanError(RuntimeError):
    """The scan could not run (unreadable rules, uncompilable pattern)."""


def load_patterns(gitleaks_path: Path = GITLEAKS_PATH) -> dict[str, re.Pattern[str]]:
    patterns = dict(BUILTIN_PATTERNS)
    try:
        data = tomllib.loads(gitleaks_path.read_text(encoding="utf-8"))
        for rule in data.get("rules", []):
            patterns[f"gitleaks:{rule['id']}"] = rule["regex"]
        return {pid: re.compile(rx) for pid, rx in patterns.items()}
    except Exception as error:  # noqa: BLE001 - a scan that cannot run is a failure
        raise SecretScanError(f"secret scan rules could not be loaded: {type(error).__name__}") from None


def scan(text: str, patterns: dict[str, re.Pattern[str]] | None = None) -> list[dict]:
    """Returns [{pattern_id, count}] for every pattern that matches `text`."""
    patterns = patterns if patterns is not None else load_patterns()
    hits = []
    for pattern_id, regex in patterns.items():
        count = len(regex.findall(text))
        if count:
            hits.append({"pattern_id": pattern_id, "count": count})
    return hits
