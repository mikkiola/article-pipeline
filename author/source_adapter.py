"""Stage 1: Source Adapter — Collector manifest -> CanonicalEvent.

Facts and evidence only. No interpretation, no narrative, no claim
about why anything happened or what it means — that belongs to Story
Builder (see story_builder.py), never here. "17 files changed" is a
fact this module produces directly; "the real problem was X" is not
something this module is allowed to say.

Read-only against Collector: this module only reads a manifest JSON
file already on disk (collector/data/manifest_<date>.json). It never
touches Collector's scripts, git history, or any other file there.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COLLECTOR_DATA_DIR = (
    Path.home() / "Dev" / "github.com" / "mikkiola" / "collector" / "data"
)

# Fallback only — used when no manifest_*.json exists at all in
# COLLECTOR_DATA_DIR. Normal resolution always goes through
# latest_collector_manifest_path() below, which picks whatever is
# actually newest on disk, so this adapter never silently reads a
# stale snapshot again.
COLLECTOR_MANIFEST_PATH = COLLECTOR_DATA_DIR / "manifest_2026-09-01.json"


def latest_collector_manifest_path() -> Path:
    """Returns the most recently modified manifest_*.json in Collector's
    data dir — never a hardcoded date. Falls back to
    COLLECTOR_MANIFEST_PATH only if no manifest exists yet."""
    candidates = list(COLLECTOR_DATA_DIR.glob("manifest_*.json"))
    if not candidates:
        return COLLECTOR_MANIFEST_PATH
    return max(candidates, key=lambda p: p.stat().st_mtime)

# Short, faithful paraphrase of Collector's own SPEC.md, G1/G3/G4 —
# not re-derived, not re-read from disk (this module stays read-only
# against Collector's manifest only), carried forward as already
# established when SPEC.md was authored this same session.
COLLECTOR_GOAL_CONTEXT = (
    "G1: break the dopamine-loop/completion-seeking pattern; "
    "G3: create an external feedback loop (not just internal activity); "
    "G4: establish a weekly rhythm."
)


@dataclass
class CanonicalEvent:
    event_id: str
    time_range_days: int
    source: str
    facts: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    context: dict[str, Any]


def adapt_collector_manifest(manifest: dict, repo_filter: str = "collector") -> CanonicalEvent:
    """Builds a CanonicalEvent from a Collector manifest, scoped to one repo.

    Every entry in the returned facts/evidence traces directly to a
    field already present in `manifest` — nothing here is computed
    from outside knowledge or invented.
    """
    event_id = f"{repo_filter}-{manifest['scan_timestamp']}"
    time_range_days = manifest["window_days"]

    matching_repos = [r for r in manifest["repos"] if r["name"] == repo_filter]
    repo_entry = matching_repos[0] if matching_repos else None

    facts: list[dict[str, Any]] = []
    if repo_entry is not None:
        facts.append({
            "type": "repo_commit_count",
            "repo": repo_entry["name"],
            "branch": repo_entry["branch"],
            "commit_count": repo_entry["commit_count"],
        })
        facts.append({
            "type": "repo_classification_counts",
            "repo": repo_entry["name"],
            "value": repo_entry["counts"]["value"],
            "explicit_service": repo_entry["counts"]["explicit_service"],
            "default_service": repo_entry["counts"]["default_service"],
        })
    facts.append({
        "type": "workspace_totals",
        "value": manifest["counts_total"]["value"],
        "explicit_service": manifest["counts_total"]["explicit_service"],
        "default_service": manifest["counts_total"]["default_service"],
    })

    # The manifest only lists per-file detail for value-classified files
    # (Step 3's own design: a distilled summary, not a full dump) — so
    # evidence here is exactly, and only, those value_files entries that
    # belong to repo_filter. If repo_filter had zero value-classified
    # files in this manifest, this list is genuinely empty — that's a
    # fact about the data, not a bug in this adapter.
    evidence = [
        dict(vf) for vf in manifest["value_files"] if vf["repo"] == repo_filter
    ]

    context: dict[str, Any] = {
        "project": repo_filter,
        "goal": COLLECTOR_GOAL_CONTEXT,
        "manifest_scan_timestamp": manifest["scan_timestamp"],
        "manifest_window_days": manifest["window_days"],
    }

    return CanonicalEvent(
        event_id=event_id,
        time_range_days=time_range_days,
        source="collector",
        facts=facts,
        evidence=evidence,
        context=context,
    )


def main() -> CanonicalEvent:
    manifest_path = latest_collector_manifest_path()
    manifest = json.loads(manifest_path.read_text())
    event = adapt_collector_manifest(manifest, repo_filter="collector")
    print(json.dumps(event.__dict__, indent=2, ensure_ascii=False))
    return event


if __name__ == "__main__":
    main()
