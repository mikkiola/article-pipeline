#!/usr/bin/env python3
"""Stage 1 of the Habr draft run: Collector input -> `selection_input.json`.

Runs with the broader GitHub App token (the integrity check needs read access
to every repository Collector's brief can name, private ones included). It
makes NO model call and fetches NO code fragments. Only units that are
integrity-valid, allow-listed, on the allow-listed branch and source-cleared
cross into stage 2; private repositories and uncleared sources never do.

An expected input-validation failure is NOT a crash: it produces a structured
preflight result (`status: failed`, with a specific reason) and exit code 0,
so the workflow goes on to record the SYSTEM_FAILURE, commit it and notify.
Only an unexpected program exception aborts the process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import date as calendar_date

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "strategy_layer"))
sys.path.insert(0, str(_ROOT / "strategy_layer" / "adapters"))
sys.path.insert(0, str(_ROOT / "author"))

from habr_draft.config import HabrConfig, load_config  # noqa: E402

TOKEN_ENV = "GITHUB_APP_TOKEN"


def _failed(reason: str, detail: str, date: str, digest: str | None = None) -> dict:
    return {"status": "failed", "reason": reason, "detail": detail, "date": date,
            "daily_brief_sha256": digest}


def integrity_unverifiable_cause(detail: str | None) -> str | None:
    """Why a unit's integrity check produced no verdict, or None when it did.

    `collector.check_integrity` fails closed and reports every failure as
    `invalid`; this separates "GitHub told us the head_sha is not on the
    branch" (a verdict) from "we could not ask / could not read the answer"
    (a technical error that must not turn into NO_ELIGIBLE_TOPIC). The match
    is on the detail texts `check_integrity` produces; the tests exercise the
    real function against injected GitHub responses so a wording change there
    is caught."""
    text = detail or ""
    if text.startswith("GitHub API request failed"):
        return "request_failed"
    if text.startswith("GitHub API returned"):
        return "unverifiable_response"
    if "is not set; cannot verify" in text:
        return "token_missing"
    return None


def validate_brief(brief: object, date: str, schema_version: int) -> tuple[str, str] | None:
    """Returns (reason, detail) for an input-validation failure, else None."""
    if not isinstance(brief, dict):
        return "daily_brief_malformed", "top-level JSON value is not an object"
    for key in ("date", "schema_version", "mode", "per_repo", "commit_messages"):
        if key not in brief:
            return "daily_brief_malformed", f"missing key {key!r}"
    if not isinstance(brief["per_repo"], list) or not isinstance(brief["commit_messages"], list):
        return "daily_brief_malformed", "per_repo/commit_messages are not lists"
    if (not isinstance(brief["date"], str) or not isinstance(brief["mode"], str)
            or type(brief["schema_version"]) is not int):
        return "daily_brief_malformed", "date/mode/schema_version have invalid types"
    try:
        calendar_date.fromisoformat(brief["date"])
    except ValueError:
        return "daily_brief_malformed", "date is not an ISO calendar date"
    if brief["schema_version"] != schema_version:
        return "daily_brief_schema_unsupported", (
            f"unsupported schema_version; expected {schema_version}"
        )
    if brief["date"] != date:
        return "daily_brief_date_mismatch", "brief date differs from requested date"
    for entry in brief["per_repo"]:
        if not isinstance(entry, dict) or not all(
            k in entry for k in ("name", "commit_count", "diffstat", "files_touched")
        ):
            return "daily_brief_malformed", "a per_repo entry lacks required keys"
        if (not isinstance(entry["name"], str)
                or any(entry.get(k) is not None and not isinstance(entry[k], str)
                       for k in ("branch", "head_sha"))
                or any(type(entry[k]) is not int or entry[k] < 0
                       for k in ("commit_count", "diffstat"))
                or not isinstance(entry["files_touched"], list)
                or any(not isinstance(path, str) for path in entry["files_touched"])):
            return "daily_brief_malformed", "a per_repo entry has invalid field types or counts"
    for entry in brief["commit_messages"]:
        if not isinstance(entry, dict) or not all(k in entry for k in ("repo", "sha", "subject")):
            return "daily_brief_malformed", "a commit_messages entry lacks repo/sha/subject"
        if (any(not isinstance(entry[k], str) for k in ("repo", "sha", "subject"))
                or any(entry.get(k) is not None and not isinstance(entry[k], str)
                       for k in ("why", "effect"))):
            return "daily_brief_malformed", "a commit_messages entry has invalid field types"
    return None


def prepare(daily_brief_path: Path, date: str, config: HabrConfig) -> dict:
    import collector
    import framing
    import pre_filter
    from authoring_context import build_authoring_contexts

    if not daily_brief_path.is_file():
        return _failed("daily_brief_missing", f"no file at the requested path for {date}", date)
    try:
        raw = daily_brief_path.read_bytes()
    except OSError:
        return _failed("daily_brief_unreadable", "could not read the requested file", date)
    digest = hashlib.sha256(raw).hexdigest()
    try:
        brief = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _failed("daily_brief_malformed", "file is not valid UTF-8 JSON", date, digest)
    problem = validate_brief(brief, date, collector.DAILY_BRIEF_SCHEMA_VERSION)
    if problem:
        return _failed(problem[0], problem[1], date, digest)
    if not os.environ.get(TOKEN_ENV):
        return _failed("github_token_missing", f"{TOKEN_ENV} is not set", date, digest)

    units = collector.adapt_daily_brief(brief)
    results = pre_filter.run_pre_filter(units)
    by_id = {r["claim_id"]: r for r in results}
    gate = pre_filter.check_gate_condition(results)

    treatments = []
    for unit in units:
        pf = by_id[unit.unit_id]
        if pf["pre_filter_classification"] == "include":
            treatments.append(
                framing.build_claim_treatment(
                    claim_id=unit.unit_id,
                    pre_filter_classification=pf["pre_filter_classification"],
                    pre_filter_reason=pf["reason"],
                    framing=(
                        f"В репозитории {unit.metadata['repo']} {unit.metadata['commit_count']} "
                        f"коммит(ов) за {date} (ветка: {unit.metadata['branch']})."
                    ),
                    derivation_kind="restatement",
                    source_status_snapshot={
                        "integrity_status": unit.integrity_status,
                        "corroboration_status": unit.corroboration_status,
                    },
                )
            )
        else:
            treatments.append(
                framing.build_claim_treatment(
                    claim_id=unit.unit_id,
                    pre_filter_classification=pf["pre_filter_classification"],
                    pre_filter_reason=pf["reason"],
                )
            )
    contexts = build_authoring_contexts(units, treatments)

    raw_repo = {entry["name"]: entry for entry in brief["per_repo"]}
    raw_commits: dict[str, list[dict]] = {}
    for entry in brief["commit_messages"]:
        raw_commits.setdefault(entry["repo"], []).append(
            {"sha": entry["sha"], "subject": entry["subject"],
             "why": entry.get("why"), "effect": entry.get("effect")}
        )

    included_repos = {ctx.repo for ctx in contexts}
    excluded = [
        {"repo": unit.metadata["repo"], "reason": "excluded_by_pre_filter",
         "detail": by_id[unit.unit_id]["reason"]}
        for unit in units
        if unit.metadata["repo"] not in included_repos
    ]
    technical_errors = []
    for unit in units:
        if unit.integrity_status != "invalid":
            continue
        meta = unit.metadata
        cause = integrity_unverifiable_cause(meta.get("integrity_check_detail"))
        if cause and config.allowed(meta["repo"], meta.get("branch")) is not None:
            technical_errors.append(
                {"repo": meta["repo"], "kind": "integrity_unverifiable", "cause": cause}
            )
    out_units = []
    for ctx in contexts:
        branch = raw_repo.get(ctx.repo, {}).get("branch")
        if ctx.commit_count <= 0 or not raw_commits.get(ctx.repo):
            excluded.append({"repo": ctx.repo, "reason": "no_commits_in_window"})
            continue
        entry = config.allowed(ctx.repo, branch)
        if entry is None:
            excluded.append({"repo": ctx.repo, "reason": "not_allow_listed_or_wrong_branch", "branch": branch})
            continue
        if not (entry.content_safety_checked and entry.authorship_checked):
            excluded.append({"repo": ctx.repo, "reason": "source_not_cleared",
                             "content_safety_checked": entry.content_safety_checked,
                             "authorship_checked": entry.authorship_checked})
            continue
        out_units.append(
            {
                "repo": ctx.repo,
                "branch": branch,
                "head_sha": raw_repo[ctx.repo].get("head_sha"),
                "commit_count": ctx.commit_count,
                "files_touched": list(ctx.files_touched),
                "commit_messages": raw_commits.get(ctx.repo, []),
            }
        )
    return {
        "status": "ok",
        "date": date,
        "daily_brief_sha256": digest,
        "gate": gate,
        "units": out_units,
        "excluded": excluded,
        "technical_errors": technical_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Habr draft run, stage 1 (no model calls).")
    parser.add_argument("--daily-brief-path", required=True)
    parser.add_argument("--date", required=True, help="Expected brief date, YYYY-MM-DD (UTC)")
    parser.add_argument("--out", required=True, help="Where to write selection_input.json (not committed)")
    args = parser.parse_args()

    result = prepare(Path(args.daily_brief_path), args.date, load_config())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"preflight status: {result['status']}"
          + (f" ({result['reason']})" if result["status"] == "failed" else
             f"; candidate units: {len(result['units'])}"))


if __name__ == "__main__":
    main()
