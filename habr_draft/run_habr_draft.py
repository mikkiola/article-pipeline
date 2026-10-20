#!/usr/bin/env python3
"""Stage 2 of the Habr draft run: topic -> draft -> checks -> record.

Runs with the NARROW read-only GitHub token (only article-pipeline, radar,
tooltempest; Contents: read) and the Habr API key, never the broader token.
Writes immutable attempt files and one immutable run record, then exits 0 for
every handled outcome (SYSTEM_FAILURE, NO_ELIGIBLE_TOPIC, calibration
included): the workflow's commit and notification steps must still run.
Nothing generated is printed.

Modes (--mode): `production` (default; refuses to start a paid call while any
mandatory configuration is unset) and `calibration` (one bounded round, no
correction cycle, never READY; needs the owner's `calibration_approval`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "strategy_layer"))
sys.path.insert(0, str(_ROOT / "strategy_layer" / "adapters"))
sys.path.insert(0, str(_ROOT / "author"))

from habr_draft import checks, fragments as fragments_mod, loop, prompts, run_record, secret_scan, topic  # noqa: E402
from habr_draft.budget import BudgetGuard  # noqa: E402
from habr_draft.config import (  # noqa: E402
    CONFIG_PATH, RUBRIC_PATH, HabrConfig, file_sha256, load_config,
    missing_for_calibration, missing_for_production,
)
from habr_draft.fragments import FetchResult  # noqa: E402
from habr_draft.llm import HabrLLM, LlmExecutionError, default_max_retries  # noqa: E402

TOKEN_ENV = "GITHUB_APP_TOKEN"
REFERENCE_PATH_ENV = "HABR_CALIBRATION_REFERENCE_PATH"


def _provenance(selection: dict, config_path: Path, env: dict) -> dict:
    try:
        import anthropic
        sdk = anthropic.__version__
    except Exception:  # noqa: BLE001
        sdk = None
    return {
        "article_pipeline_sha": env.get("ARTICLE_PIPELINE_SHA"),
        "collector_sha": env.get("COLLECTOR_SHA"),
        "daily_brief_sha256": selection.get("daily_brief_sha256"),
        "acceptance_config_sha256": file_sha256(config_path),
        "rubric_sha256": file_sha256(RUBRIC_PATH),
        "anthropic_sdk_version": sdk,
    }


def _cluster_for(unit: dict) -> tuple[dict, dict]:
    """(cluster, brief-shaped dict) for the chosen repository, built with the
    existing `build_clusters` so fact ids are the ones the LinkedIn path uses."""
    import daily_linkedin_author

    evidence = [c for c in unit["commit_messages"] if c.get("why") or c.get("effect")]
    brief = {
        "per_repo": [
            {
                "name": unit["repo"],
                "commit_count": unit["commit_count"],
                "commit_messages": [c["subject"] for c in unit["commit_messages"]],
                "commit_evidence": evidence,
                "files_touched": unit["files_touched"],
            }
        ]
    }
    return daily_linkedin_author.build_clusters(brief)[0], brief


def _to_draft(response: dict, purpose: str) -> loop.Draft:
    title, body = response.get("title"), response.get("body_markdown")
    if not isinstance(title, str) or not isinstance(body, str) or not body.strip():
        raise LlmExecutionError("execution_error", f"{purpose}: draft response malformed")
    return loop.Draft(title, body, response)


def _read_selection(path: Path) -> dict:
    """The selection input crosses a job boundary as a build artifact, so an
    unreadable or structurally wrong file is an input-validation failure of
    this run, not a crash that would skip the run record and notification."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "failed", "reason": "selection_input_unreadable",
                "detail": "selection_input.json is missing or is not valid UTF-8 JSON"}
    if not isinstance(value, dict):
        return {"status": "failed", "reason": "selection_input_malformed",
                "detail": "top-level JSON value is not an object"}
    if value.get("status") == "ok":
        units = value.get("units")
        if not isinstance(units, list) or not all(_valid_unit(u) for u in units):
            return {"status": "failed", "reason": "selection_input_malformed",
                    "detail": "status ok without a well-formed units list"}
    return value


def _valid_unit(unit: object) -> bool:
    return (
        isinstance(unit, dict)
        and isinstance(unit.get("repo"), str) and bool(unit["repo"])
        and isinstance(unit.get("commit_count"), int)
        and isinstance(unit.get("files_touched"), list)
        and isinstance(unit.get("commit_messages"), list)
        and all(isinstance(c, dict) and isinstance(c.get("sha"), str)
                and isinstance(c.get("subject"), str) for c in unit["commit_messages"])
    )


def run(
    *,
    selection_path: Path,
    date: str,
    mode: str,
    output_dir: Path,
    config: HabrConfig,
    config_path: Path = CONFIG_PATH,
    env: dict | None = None,
    caller: Callable[..., dict] | None = None,
    fetch_fn: Callable | None = None,
    visibility: Callable[[str], bool] | None = None,
    now: datetime | None = None,
) -> dict:
    env = dict(os.environ if env is None else env)
    now = now or datetime.now(timezone.utc)
    run_id = f"habr-draft-{date}-{now.strftime('%H%M%S')}"
    selection = _read_selection(selection_path)

    record: dict = {
        "run_id": run_id,
        "date": date,
        "mode": mode,
        "provenance": _provenance(selection, config_path, env),
        "model": config.model,
        "topic": None,
        "fragments": {"used": [], "excluded": [], "dropped": []},
        "rounds": [],
        "enrichment": {"status": "skipped", "reason": "not performed in MVP"},
        "budget": None,
        "terminal_outcome": None,
        "observable_outcome": None,
        "failure_kind": None,
        "reason": None,
        "attempt_files": [],
    }

    def finish(terminal: str | None, observable: str, kind: str | None = None,
               reason: str | None = None) -> dict:
        record["terminal_outcome"] = terminal
        record["observable_outcome"] = observable
        record["failure_kind"] = kind
        record["reason"] = reason
        record["report"] = run_record.build_report(terminal, mode, kind)
        if mode == "calibration":
            record["calibration_result"] = (
                "recorded" if observable == "CALIBRATION_RECORDED" else "not_recorded"
            )
        record["run_record_file"] = run_record.write_run_record(output_dir, run_id, record)
        print(f"run {run_id}: {observable}" + (f" ({kind}: {reason})" if kind else ""))
        return record

    record["preflight"] = {
        "status": selection.get("status"),
        "reason": selection.get("reason"),
        "detail": selection.get("detail"),
    }

    # -- configuration gate: first, before any candidate is looked at. Unset
    # mandatory configuration must always end as missing_configuration; it must
    # never surface as NO_ELIGIBLE_TOPIC or as a topic-selection side effect.
    missing = missing_for_calibration(config) if mode == "calibration" else missing_for_production(config)
    reference_text = None
    if mode == "calibration":
        ref_path = env.get(REFERENCE_PATH_ENV)
        if not ref_path or not Path(ref_path).is_file():
            missing.append(REFERENCE_PATH_ENV)
        else:
            try:
                reference_text = Path(ref_path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                missing.append(REFERENCE_PATH_ENV)  # unreadable counts as not supplied
    if missing:
        record["missing_configuration"] = sorted(set(missing))
        record["q_threshold_unset"] = "q_threshold" in missing
        return finish(loop.SYSTEM_FAILURE, loop.SYSTEM_FAILURE, "missing_configuration",
                      "required configuration unset: " + ", ".join(sorted(set(missing))))

    # -- stage 1 preflight result
    if selection.get("status") != "ok":
        return finish(loop.SYSTEM_FAILURE, loop.SYSTEM_FAILURE, "input_validation",
                      f"{selection.get('reason')}: {selection.get('detail')}")

    # -- topic selection (GitHub only; no paid call)
    token = env.get(TOKEN_ENV)
    if visibility is None:
        visibility = lambda repo: fragments_mod.repo_visibility(repo, token)  # noqa: E731
    raw_fetcher = fetch_fn or (
        lambda unit: fragments_mod.fetch_fragments(unit["repo"], unit["commit_messages"], token, config)
    )
    cap = config.budget.max_fragment_chars_per_attempt

    def fetcher(unit: dict):
        """A fragment that does not fit the volume cap is not usable: a
        candidate left with none is skipped like any other candidate with no
        usable fragment, so no paid call is made for it."""
        result = raw_fetcher(unit)
        kept, dropped = fragments_mod.select_within_cap(result.fragments, cap)
        by_id = {f["id"]: f for f in result.fragments}
        capped = [
            {"repo": by_id[d["id"]]["repo"], "sha": by_id[d["id"]]["sha"],
             "path": by_id[d["id"]]["path"], "reason": "volume_cap"}
            for d in dropped
        ]
        return FetchResult(fragments=kept, exclusions=list(result.exclusions) + capped,
                           errors=list(result.errors))

    chosen = topic.choose_topic(selection["units"], fetcher, visibility)
    stage_1_errors = selection.get("technical_errors") or []
    record["topic"] = {"status": chosen.status, "basis": chosen.basis, "walk": chosen.walk,
                       "excluded_by_stage_1": selection.get("excluded", []),
                       "stage_1_technical_errors": stage_1_errors}
    if chosen.status == "fetch_error":
        return finish(loop.SYSTEM_FAILURE, loop.SYSTEM_FAILURE, "execution_error", "fragment_fetch_error")
    if chosen.status == "no_eligible_topic":
        if stage_1_errors:
            # Stage 1 could not verify a candidate: "nothing qualified" is not
            # an observation about the data, so it is not NO_ELIGIBLE_TOPIC.
            return finish(loop.SYSTEM_FAILURE, loop.SYSTEM_FAILURE, "execution_error",
                          "integrity_unverifiable")
        return finish(None, "NO_ELIGIBLE_TOPIC", None, "no_eligible_topic")
    unit = chosen.unit
    record["topic"]["repo"] = unit["repo"]

    kept = chosen.fragments  # already within the volume cap (see `fetcher`)
    walked = [e for step in chosen.walk for e in step.get("exclusions", [])]
    record["fragments"] = {
        "used": [{k: f[k] for k in ("id", "repo", "sha", "path", "content_sha256")} for f in kept],
        "excluded": [e for e in walked if e.get("reason") != "volume_cap"],
        "dropped": [e for e in walked if e.get("reason") == "volume_cap"],
    }
    try:
        cluster, brief = _cluster_for(unit)
    except Exception as error:  # noqa: BLE001
        return finish(loop.SYSTEM_FAILURE, loop.SYSTEM_FAILURE, "execution_error",
                      f"cluster construction failed ({type(error).__name__})")
    allowed_ids = {fact["id"] for fact in cluster["facts"]} | {f["id"] for f in kept}

    guard = BudgetGuard(
        limit_usd=config.budget.max_run_spend_usd,
        price_in_per_mtok=config.budget.price_in_per_mtok,
        price_out_per_mtok=config.budget.price_out_per_mtok,
        max_retries=default_max_retries(),
    )
    llm = HabrLLM(config, guard, caller=caller)
    gen_tokens, judge_tokens = config.budget.max_tokens_generation, config.budget.max_tokens_judge
    patterns = secret_scan.load_patterns()

    def generate() -> loop.Draft:
        return _to_draft(
            llm.ask(prompts.build_generation_request(cluster, kept), max_tokens=gen_tokens, purpose="generation"),
            "generation",
        )

    def revise(previous: loop.Draft | None, failed: list[dict]) -> loop.Draft:
        return _to_draft(
            llm.ask(
                prompts.build_revision_request(cluster, kept, previous.body if previous else None, failed),
                max_tokens=gen_tokens, purpose="revision",
            ),
            "revision",
        )

    def evaluate(draft: loop.Draft) -> list[checks.CheckResult]:
        l1_judge = llm.ask(prompts.build_l1_request(draft.body, cluster, kept),
                           max_tokens=judge_tokens, purpose="l1_judge")
        q_judge = llm.ask(prompts.build_q_request(draft.body), max_tokens=judge_tokens, purpose="q_judge")
        return [
            checks.evaluate_l1(draft.response, brief, allowed_ids, l1_judge),
            checks.check_habr_rules(draft.body, config.a_rules),
            checks.check_project_requirements(draft.body, kept),
            checks.evaluate_q(q_judge, config.q_threshold),
        ]

    attempt_files: dict[int, dict] = {}

    def on_attempt(attempt: loop.Attempt) -> None:
        if attempt.saved:
            attempt_files[attempt.number] = run_record.write_attempt(
                output_dir, attempt.number, attempt.draft.title, attempt.draft.body
            )

    result = loop.run_rounds(
        generate=generate, revise=revise, evaluate=evaluate,
        scan=lambda text: secret_scan.scan(text, patterns),
        mode=mode, on_attempt=on_attempt,
    )
    record["rounds"] = [
        {
            "number": a.number,
            "verdict": a.verdict,
            "saved": a.saved,
            "attempt_file": attempt_files.get(a.number),
            "secret_hits": a.secret_hits,
            "checks": [c.to_dict() for c in a.checks],
        }
        for a in result.attempts
    ]
    record["attempt_files"] = [attempt_files[n] for n in sorted(attempt_files)]
    record["best_attempt"] = result.best_attempt
    record["budget"] = guard.report()
    terminal, kind, reason = result.terminal_outcome, result.failure_kind, result.reason

    if mode == "calibration" and terminal is None and reference_text is not None:
        q_scores = [c for a in result.attempts for c in a.checks if c.name == "q_infostyle"]
        record["calibration"] = {
            "q_score": q_scores[0].score if q_scores else None,
            "q_findings": q_scores[0].findings if q_scores else [],
            "reference": {
                "sha256": hashlib.sha256(reference_text.encode("utf-8")).hexdigest(),
                "length": len(reference_text),
            },
        }
        try:
            ref = llm.ask(prompts.build_reference_q_request(reference_text),
                          max_tokens=judge_tokens, purpose="reference_q_judge")
            score = ref.get("score")
            findings = [
                {"criterion": f.get("criterion"), "severity": f.get("severity")}
                for f in (ref.get("findings") or []) if isinstance(f, dict)
            ]
            record["calibration"]["reference"].update(q_score=score, q_findings=findings)
        except LlmExecutionError as error:
            terminal, kind, reason = loop.SYSTEM_FAILURE, error.kind, error.reason
        record["budget"] = guard.report()

    if terminal is None:
        observable = "CALIBRATION_RECORDED"
    else:
        observable = terminal
    return finish(terminal, observable, kind, reason)


def main() -> None:
    parser = argparse.ArgumentParser(description="Habr draft run, stage 2.")
    parser.add_argument("--selection-input", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--mode", choices=("production", "calibration"), default="production")
    args = parser.parse_args()
    run(
        selection_path=Path(args.selection_input),
        date=args.date,
        mode=args.mode,
        output_dir=run_record.output_dir_from_env(),
        config=load_config(),
    )


if __name__ == "__main__":
    main()
