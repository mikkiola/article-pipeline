#!/usr/bin/env python3
"""Daily LinkedIn Auto-Publish — the scheduled entrypoint for SPEC.md
Milestone M2 (bootstrap-gated).

Full pipeline, real wiring, matching the already-proven shape of
strategy_layer/run_linkedin_pilot.py (which stops at prompt
construction) extended past it into a real model call, a real
LinkedIn publish, and a real Publication Registry write:

Collector daily_brief.json -> collector adapter -> CanonicalUnit list
-> pre_filter (bootstrap gate) -> [gate blocks: write a block Registry
record, stop] / [gate passes: framing -> Strategy Layer verdict ->
AuthoringContext -> daily_brief-shaped dict -> LLM prompt -> LLM call
-> LinkedIn publish -> write a pass Registry record].

Known data-model limitation, stated plainly, not silently resolved:
publication_registry.contract.PublicationRecord.claim_id is a single
string (SPEC.md Functional Requirement #4), but a real LinkedIn post
built from a daily_brief can legitimately aggregate multiple included
claims (one per included repo) into one post, and a bootstrap-gate
block is a run-level outcome with no single claim to name at all. This
module uses the first unit in the run's own order as a representative
claim_id in both cases — an honest, documented simplification, not an
invented multi-ID format smuggled into a field the schema calls
singular. Revisiting PublicationRecord to support multiple claims per
publication is out of this task's scope (see
docs/adr/0054-m2-ships-core-linkedin-publishing-without-safety-pause-
trigger-or-proactive-credential-alerting.md).

SAFETY_PAUSE and the token preflight are both checked before any
network call is attempted (docs/adr/0054's Decision section covers
why this task builds the check but not SAFETY_PAUSE's trigger, and why
the preflight, not a proactive alert, is M2's complete answer to token
expiry).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "strategy_layer"))
sys.path.insert(0, str(_REPO_ROOT / "strategy_layer" / "adapters"))
sys.path.insert(0, str(_REPO_ROOT / "author"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import framing  # noqa: E402
import pre_filter  # noqa: E402
import write_verdict  # noqa: E402
import collector as collector_adapter  # noqa: E402
from authoring_context import build_authoring_contexts  # noqa: E402
from linkedin_verdict_reader import build_daily_brief_from_authoring_contexts  # noqa: E402
import daily_linkedin_author  # noqa: E402


def _load_isolated(module_name: str, file_path: Path):
    """Loads `file_path` as `module_name`, replacing (not merging with)
    whatever module is currently cached under that name in sys.modules.

    Needed specifically because strategy_layer/contract.py (CanonicalUnit,
    already imported above via pre_filter/authoring_context/etc.'s own
    bare `from contract import ...`) and publication_registry/contract.py
    (PublicationRecord) share the literal filename "contract" — a
    collision this project's existing bare-import + sys.path convention
    doesn't handle when both are needed in the same process. Every
    module already imported above bound its own CanonicalUnit reference
    at its own import time, so overwriting sys.modules["contract"] here
    doesn't retroactively affect them — this is safe precisely because
    nothing below this point needs strategy_layer's contract.py again.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_registry_dir = _REPO_ROOT / "publication_registry"
sys.modules["contract"] = _load_isolated("contract", _registry_dir / "contract.py")
PublicationRecord = sys.modules["contract"].PublicationRecord
registry_writer = _load_isolated("publication_registry_writer", _registry_dir / "writer.py")

import linkedin_client  # noqa: E402
from safety_pause import SafetyPauseState, check_safety_pause_state  # noqa: E402

GATE_VERSION = "v1"


def resolve_daily_brief_path(
    explicit_path: str | None = None,
    workspace_root: Path | None = None,
    date: str | None = None,
) -> Path:
    """Resolves the daily_brief_<date>.json to read.

    An explicit path always wins (manual/test invocation). Otherwise,
    matching strategy_layer/adapters/collector.py's WORKSPACE_ROOT
    convention (env var, falling back to the local-dev sibling-checkout
    layout) and today's UTC date, matching
    author/daily_linkedin_author.py's own `date_token` convention.
    """
    if explicit_path:
        return Path(explicit_path)

    root = workspace_root or Path(
        os.environ.get("WORKSPACE_ROOT", str(Path.home() / "Dev" / "github.com" / "mikkiola"))
    )
    date_token = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return root / "collector" / "data" / f"daily_brief_{date_token}.json"


def build_content_id(date: str) -> str:
    """content_id = linkedin-{date} — caller-supplied, per
    docs/adr/0053-content-id-ownership-moves-to-caller.md, and stable
    across a retry of the same day's publication attempt because it's
    keyed to the daily_brief's own `date` field, not wall-clock run
    time."""
    return f"linkedin-{date}"


def pick_representative_claim_id(unit_ids: list[str]) -> str:
    """See module docstring's "Known data-model limitation" note."""
    if not unit_ids:
        raise ValueError("cannot pick a representative claim_id from an empty unit list")
    return unit_ids[0]


def _restatement_framing(unit_metadata: dict) -> str:
    # Same template as strategy_layer/run_linkedin_pilot.py's own
    # helper — reused, not reinvented: every Collector-sourced unit's
    # derivation_kind is "restatement" (bare commit/diffstat counts,
    # no evaluation or causal claim), which a template can honestly
    # represent without the interactive judgment an "evaluation" or
    # "causal_claim" framing would need (strategy_layer/
    # run_collector_pilot.py's own docstring states this reasoning).
    return (
        f"{unit_metadata['repo']}: {unit_metadata['commit_count']} commit(s), "
        f"{unit_metadata['diffstat']} lines changed today (branch: {unit_metadata['branch']})."
    )


def build_block_record(
    content_id: str,
    pre_filter_results: list[dict],
    now: datetime,
) -> PublicationRecord:
    """Bootstrap-gate block (SPEC.md Functional Requirement #9): zero
    units survived pre_filter. block_reason cites the first excluded
    unit's own pre_filter reason as a representative sample, plus the
    aggregate exclusion count, rather than fabricating one gate-level
    reason string pre_filter itself never produces."""
    representative_claim_id = pick_representative_claim_id(
        [r["claim_id"] for r in pre_filter_results]
    )
    first_reason = pre_filter_results[0]["reason"]
    block_reason = (
        f"Bootstrap gate: zero included units "
        f"({len(pre_filter_results)}/{len(pre_filter_results)} excluded). "
        f"First excluded reason ({representative_claim_id}): {first_reason}"
    )
    return PublicationRecord(
        content_id=content_id,
        platform="linkedin",
        url="",
        published_at=now,
        claim_id=representative_claim_id,
        gate_policy="bootstrap",
        gate_version=GATE_VERSION,
        gate_status="block",
        block_reason=block_reason,
        gate_evaluated_at=now,
    )


def build_pass_record(
    content_id: str,
    url: str,
    claim_id: str,
    now: datetime,
) -> PublicationRecord:
    return PublicationRecord(
        content_id=content_id,
        platform="linkedin",
        url=url,
        published_at=now,
        claim_id=claim_id,
        gate_policy="bootstrap",
        gate_version=GATE_VERSION,
        gate_status="pass",
        block_reason=None,
        gate_evaluated_at=now,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "SPEC.md Milestone M2 — daily LinkedIn auto-publish, bootstrap-gated. "
            "Reads a Collector daily_brief_<date>.json, runs it through the "
            "bootstrap gate, and on pass generates + publishes one LinkedIn post."
        )
    )
    parser.add_argument(
        "--daily-brief-path",
        default=None,
        help="Explicit path to a daily_brief_<date>.json. Defaults to today's "
        "UTC date under $WORKSPACE_ROOT/collector/data/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    state = check_safety_pause_state()
    if state == SafetyPauseState.OPEN:
        print("SAFETY_PAUSE is OPEN — skipping this run, no publish attempted.")
        return

    linkedin_client.check_token_preflight()

    daily_brief_path = resolve_daily_brief_path(args.daily_brief_path)
    print(f"daily_brief source: {daily_brief_path}")
    with open(daily_brief_path, "r", encoding="utf-8") as f:
        daily_brief = json.loads(f.read())

    units = collector_adapter.adapt_daily_brief(daily_brief)
    print(f"units built: {len(units)}")

    pre_filter_results = pre_filter.run_pre_filter(units)
    gate_result = pre_filter.check_gate_condition(pre_filter_results)
    print(f"gate_result: {gate_result}")
    for unit in units:
        print(
            f"  {unit.metadata.get('repo', '<missing>')}: "
            f"integrity_status={unit.integrity_status} "
            f"detail={unit.metadata.get('integrity_check_detail', '<missing>')}"
        )

    content_id = build_content_id(daily_brief["date"])

    # Read-before-publish guard: publish_post() has no client-side
    # idempotency key, and write_record()'s own existing-file check only
    # runs after a post is already live. A `pass` record means this
    # content_id already published; a `block` record does not (nothing
    # was posted). An unparseable record raises inside read_record().
    existing_record = registry_writer.read_record(content_id)
    if existing_record is not None and existing_record.gate_status == "pass":
        print(
            f"Registry already has a published record for {content_id} — "
            f"skipping, no publish attempted."
        )
        return

    now = datetime.now(timezone.utc)

    if gate_result["status"] == "gated":
        record = build_block_record(content_id, pre_filter_results, now)
        path = registry_writer.write_record(record)
        print(f"Bootstrap gate blocked — no publish. Registry record: {path}")
        return

    results_by_id = {r["claim_id"]: r for r in pre_filter_results}
    claim_treatments = []
    for unit in units:
        pf = results_by_id[unit.unit_id]
        if pf["pre_filter_classification"] == "include":
            treatment = framing.build_claim_treatment(
                claim_id=unit.unit_id,
                pre_filter_classification=pf["pre_filter_classification"],
                pre_filter_reason=pf["reason"],
                framing=_restatement_framing(unit.metadata),
                derivation_kind="restatement",
                source_status_snapshot={
                    "integrity_status": unit.integrity_status,
                    "corroboration_status": unit.corroboration_status,
                },
            )
        else:
            treatment = framing.build_claim_treatment(
                claim_id=unit.unit_id,
                pre_filter_classification=pf["pre_filter_classification"],
                pre_filter_reason=pf["reason"],
            )
        claim_treatments.append(treatment)

    run_id = now.strftime("%Y%m%dT%H%M%S")
    verdict = write_verdict.build_verdict(run_id, gate_result, claim_treatments)
    verdict_path = write_verdict.write_outputs(run_id, verdict)
    print(f"Strategy Layer verdict written: {verdict_path}")

    contexts = build_authoring_contexts(units, claim_treatments)
    daily_brief_shaped = build_daily_brief_from_authoring_contexts(
        contexts, date=daily_brief["date"]
    )
    prompt = daily_linkedin_author.build_prompt(daily_brief_shaped)
    response = daily_linkedin_author.call_model(prompt)
    daily_linkedin_author.validate_structured_response(
        response, daily_brief_shaped["mode"], daily_brief_shaped
    )
    post_text = response["post"]

    post_url = linkedin_client.publish_post(post_text)
    print(f"Published: {post_url}")

    included_claim_id = pick_representative_claim_id([ctx.claim_id for ctx in contexts])
    record = build_pass_record(content_id, post_url, included_claim_id, now)
    path = registry_writer.write_record(record)
    print(f"Registry record: {path}")


if __name__ == "__main__":
    main()
