"""Automatic topic selection (SPEC.md M9 requirement 51).

Deterministic and recorded. Candidates are the repositories stage 1 delivered
(already: integrity valid, allow-listed, branch main). They are ranked, then
walked IN ORDER until the first repository with a usable, passing fragment.
A technical fetch error is recorded distinctly from "no eligible topic".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


def rank_candidates(units: list[dict]) -> list[dict]:
    """Ranking basis: number of commits that state a reason or an effect,
    then commit count, then number of touched files, then repository name."""

    def key(unit: dict):
        stated = sum(1 for c in unit.get("commit_messages", []) if c.get("why") or c.get("effect"))
        return (-stated, -unit.get("commit_count", 0), -len(unit.get("files_touched", [])), unit["repo"])

    return sorted(units, key=key)


@dataclass
class TopicResult:
    status: str  # "chosen" | "no_eligible_topic" | "fetch_error"
    unit: dict | None = None
    fragments: list[dict] = field(default_factory=list)
    walk: list[dict] = field(default_factory=list)  # per-candidate record
    basis: str = ""


def choose_topic(
    units: list[dict],
    fetch: Callable[[dict], "object"],
    is_visible: Callable[[str], bool | None],
) -> TopicResult:
    """`fetch(unit)` returns a fragments.FetchResult for the candidate.
    `is_visible(repo)` is the live public-repository check, tri-state:
    True = confirmed public, False = confirmed not public, None = the check
    itself could not be completed (a technical error, not a verdict)."""
    ranked = rank_candidates(units)
    walk: list[dict] = []
    any_error = False
    for position, unit in enumerate(ranked, start=1):
        record = {"rank": position, "repo": unit["repo"]}
        visible = is_visible(unit["repo"])
        if visible is None:
            any_error = True
            record.update(outcome="skipped", reason="visibility_check_error",
                          errors=[{"repo": unit["repo"], "kind": "visibility_check"}])
            walk.append(record)
            continue
        if not visible:
            record.update(outcome="skipped", reason="not_confirmed_public")
            walk.append(record)
            continue
        fetched = fetch(unit)
        record["exclusions"] = fetched.exclusions
        record["errors"] = fetched.errors
        if fetched.errors:
            any_error = True
        if fetched.fragments:
            record["outcome"] = "chosen"
            walk.append(record)
            return TopicResult(
                "chosen", unit, fetched.fragments, walk,
                basis=(
                    "ranked by commits stating a reason/effect, then commit count, "
                    f"then files touched, then name; first usable candidate (rank {position})"
                ),
            )
        record["outcome"] = "no_usable_fragment"
        walk.append(record)
    if any_error:
        return TopicResult("fetch_error", None, [], walk, basis="no usable fragment and at least one technical fetch error")
    return TopicResult("no_eligible_topic", None, [], walk, basis="every candidate examined without error; none had a usable fragment")
