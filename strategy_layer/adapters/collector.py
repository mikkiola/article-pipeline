"""Collector's ACL adapter — Collector manifest_*.json/daily_brief_*.json
-> list[CanonicalUnit] (SPEC.md's source-independence extension,
Milestone M3, Part 1).

Read-only against Collector, same convention as author/source_adapter.py:
reads JSON files already on disk and (for the integrity check) runs
read-only `git` commands against local workspace checkouts — never
writes to Collector's own repository or scripts.

Every unit this adapter produces has corroboration_status=
"not_applicable" — Collector's raw telemetry (a commit happened, a
file was touched) makes no falsifiable assertion to corroborate.
Derived-claim synthesis (e.g. "activity increased this week") is out
of scope this sprint (SPEC.md's Out of Scope section) — every raw
record passes through as its own individual unit, unsynthesized.

**Real integrity check, not static** (owner decision, SPEC.md's
"Collector's Integrity Check" section): repo+branch existence
(`git rev-parse --verify`) plus commit_count reconciliation
(`git rev-list --count`, anchored to the same historical window
Collector's own scan covered — see check_integrity()'s docstring for
why the window must be explicitly anchored, not left to git's
implicit "now"). Labeled `integrity_check_method=
"commit_count_reconciliation"` — a single-metric reconciliation check
with bounded coverage, not a claim of full cryptographic provenance
(no commit hashes exist anywhere in Collector's data to check against
— confirmed by direct inspection before this design was chosen).

**Two real gaps in daily_brief's own data, not filled in silently**
(see adapt_daily_brief()'s docstring): no `branch` field (Collector's
own daily_brief.py drops it), and no precise scan timestamp (only a
date token). Both are documented approximations, not hidden defaults.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from os import environ
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contract import CanonicalUnit  # noqa: E402

WORKSPACE_ROOT = Path(
    environ.get("WORKSPACE_ROOT", str(Path.home() / "Dev" / "github.com" / "mikkiola"))
)

INTEGRITY_CHECK_METHOD = "commit_count_reconciliation"

# Anti-"junk drawer" safeguard (ADR-0045): the exact set of metadata
# keys each source_type is allowed to produce. A future adapter (e.g.
# Brain's, not built this sprint) adds its own entry here, not a new
# mechanism. check_metadata_whitelist() below is the enforcement point.
METADATA_WHITELIST = {
    "collector_manifest": {
        "source_type",
        "repo",
        "branch",
        "commit_count",
        "counts",
        "window_days",
        "integrity_check_detail",
    },
    "collector_daily_brief": {
        "source_type",
        "repo",
        "branch",
        "commit_count",
        "diffstat",
        "files_touched",
        "commit_messages",
        "mode",
        "window_days",
        "integrity_check_detail",
    },
}


def check_metadata_whitelist(source_type: str, metadata: dict) -> None:
    """Raises ValueError if `metadata` carries any key not on
    `source_type`'s whitelist. Returns None (no exception) when clean.
    """
    if source_type not in METADATA_WHITELIST:
        raise ValueError(
            f"unknown source_type {source_type!r} — no metadata whitelist "
            f"defined for it (known: {sorted(METADATA_WHITELIST)})"
        )
    allowed = METADATA_WHITELIST[source_type]
    extra = set(metadata) - allowed
    if extra:
        raise ValueError(
            f"metadata for source_type={source_type!r} carries key(s) not "
            f"on its whitelist: {sorted(extra)} (allowed: {sorted(allowed)})"
        )

_WINDOW_RE = re.compile(r"^(\d+)\.days?$")


def parse_window_days(window: str) -> int:
    """Parses a Collector `--since`-style window string ('1.day' /
    '7.days', same format tier0_scan.py's own parse_window_days()
    accepts) into an integer day count."""
    match = _WINDOW_RE.match(window)
    if not match:
        raise ValueError(f"cannot parse a window day-count from {window!r}")
    return int(match.group(1))


def _repo_path(repo_name: str) -> Path:
    return WORKSPACE_ROOT / repo_name


def _run_git(repo_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
    )


def resolve_current_branch(repo_name: str) -> str | None:
    """Live HEAD branch for a repo — used only when the source record
    doesn't carry its own branch (daily_brief's per_repo entries drop
    it; manifest's repos entries carry branch directly and don't call
    this). Assumes the branch hasn't changed since the record was
    produced — a stated, not hidden, limitation. Returns None if the
    repo isn't a local checkout at all."""
    repo_path = _repo_path(repo_name)
    if not repo_path.is_dir():
        return None
    result = _run_git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def check_integrity(
    repo_name: str,
    branch: str,
    reported_commit_count: int,
    window_days: int,
    anchor: datetime,
) -> tuple[str, str]:
    """Returns (integrity_status, detail) for one repo record.

    Two checks, in order: (1) the named repo exists as a local
    checkout and the named branch exists in it; (2) `git rev-list
    --count` for the SAME historical window Collector's own scan
    covered reconciles exactly against the reported commit_count.

    The window must be explicitly anchored via --until=<anchor>, not
    left to git's implicit "now": Collector's own tier0_scan.py always
    scans relative to whenever IT runs (`--since=<window>` with no
    upper bound) — re-running an equivalent check later without
    pinning the same upper bound would compare a different absolute
    time range, not reconstruct the original one. `anchor` is the
    manifest's own `scan_timestamp` for manifest-sourced units, or an
    end-of-day approximation for daily_brief-sourced units (see
    adapt_daily_brief()).

    Tolerance: exact match, not a fudge factor. Collector's own
    commit_count (tier0_scan.py's `len(git log --since=...)` output)
    and this reconciliation (`git rev-list --count --since=...
    --until=...`) walk the same underlying git revision history via
    the same machinery — given the correctly anchored window, they
    should produce an identical count. A mismatch is itself a real
    signal (history rewritten since the scan, or a repo/branch
    mismatch), not measurement noise to average over.
    """
    repo_path = _repo_path(repo_name)
    if not repo_path.is_dir():
        return "invalid", f"local checkout not found at {repo_path}"

    verify = _run_git(repo_path, "rev-parse", "--verify", branch)
    if verify.returncode != 0:
        return "invalid", f"branch {branch!r} not found in {repo_path}"

    # Absolute timestamps for BOTH bounds, not git's relative `--since=N.days`
    # shorthand — that shorthand always resolves relative to actual
    # wall-clock "now" when the command runs, not relative to `--until`.
    # Combining it with an explicit --until anchor silently shifts the
    # window forward by however much real time has passed since `anchor`,
    # undercounting. Confirmed as a real bug via a live run against this
    # workspace's actual repos (2026-09-15): 5 of 7 repos showed a
    # commit_count mismatch, reconciled consistently LOWER than reported
    # — the direction only this specific bug produces (a genuine history
    # rewrite would go either way; a narrowed window only ever loses
    # commits). Fixed by computing an absolute --since instead.
    since = (anchor - timedelta(days=window_days)).isoformat()
    until = anchor.isoformat()
    count_result = _run_git(
        repo_path, "rev-list", "--count", branch, f"--since={since}", f"--until={until}"
    )
    if count_result.returncode != 0:
        return "invalid", f"git rev-list failed: {count_result.stderr.strip()}"

    live_count = int(count_result.stdout.strip())
    if live_count != reported_commit_count:
        return "invalid", (
            f"commit_count mismatch: reported={reported_commit_count}, "
            f"reconciled={live_count} (window: {since} until {until})"
        )

    return "valid", (
        f"reconciled: {live_count} commits matched reported "
        f"{reported_commit_count} (window: {since} until {until})"
    )


def adapt_manifest(manifest: dict) -> list[CanonicalUnit]:
    """Builds one CanonicalUnit per repo entry in a Collector
    manifest_*.json. `branch` and `scan_timestamp` both come directly
    from the manifest — no approximation needed here (unlike
    adapt_daily_brief() below)."""
    scan_timestamp = datetime.fromisoformat(manifest["scan_timestamp"])
    window_days = manifest["window_days"]

    units = []
    for repo in manifest["repos"]:
        integrity_status, detail = check_integrity(
            repo["name"], repo["branch"], repo["commit_count"], window_days, scan_timestamp
        )
        units.append(
            CanonicalUnit(
                unit_id=f"collector:manifest:{manifest['scan_timestamp']}:{repo['name']}",
                source="collector",
                created_at=scan_timestamp,
                integrity_status=integrity_status,
                integrity_check_method=INTEGRITY_CHECK_METHOD,
                corroboration_status="not_applicable",
                assertion_text=None,
                metadata={
                    "source_type": "collector_manifest",
                    "repo": repo["name"],
                    "branch": repo["branch"],
                    "commit_count": repo["commit_count"],
                    "counts": repo.get("counts"),
                    "window_days": window_days,
                    "integrity_check_detail": detail,
                },
            )
        )
    return units


def adapt_daily_brief(daily_brief: dict) -> list[CanonicalUnit]:
    """Builds one CanonicalUnit per repo entry in a Collector
    daily_brief_<date>.json.

    Two real gaps in daily_brief's own data, not filled in silently:
    - No `branch` field — Collector's own daily_brief.py
      (compute_metrics()) drops it when reducing tier0_scan.py's raw
      output. Resolved live via resolve_current_branch() (the repo's
      current HEAD) — assumes the branch hasn't changed since the
      brief was generated. A repo with no local checkout at all
      resolves to None, which this function marks integrity_status=
      "invalid" directly, without attempting a git call that would
      only fail anyway.
    - No precise scan timestamp — only a `date` token (day
      granularity). daily_brief.py does not preserve raw_scan's own
      `scan_timestamp`. Approximated as that date's 23:59:59 UTC — the
      real scan could have run at any point during that day, not
      necessarily at its end; stated here as a genuine approximation,
      not hidden.

    `commit_messages` (M4, 2026-09-15): daily_brief's own top-level
    `commit_messages` array is FLAT — a cross-repo list, not per-repo
    attributed (daily_brief.py's compute_metrics() already collapses it
    that way before Collector ever writes the file). Every unit built
    from the same daily_brief carries the identical commit_messages
    list in its metadata, by construction — not a duplication bug.
    `mode` is carried through unchanged (Collector's own "fact" /
    "idea_fallback" decision, already made upstream — this adapter
    doesn't interpret it, only passes it along, same "trust upstream
    decisions" principle daily_linkedin_author.py's own module
    docstring already states for this field).
    """
    window_days = parse_window_days(daily_brief["window"])
    anchor = datetime.fromisoformat(daily_brief["date"]).replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc
    )

    units = []
    for repo in daily_brief["per_repo"]:
        branch = resolve_current_branch(repo["name"])
        if branch is None:
            integrity_status = "invalid"
            detail = f"local checkout not found for {repo['name']!r} (branch could not be resolved)"
        else:
            integrity_status, detail = check_integrity(
                repo["name"], branch, repo["commit_count"], window_days, anchor
            )
        units.append(
            CanonicalUnit(
                unit_id=f"collector:daily_brief:{daily_brief['date']}:{repo['name']}",
                source="collector",
                created_at=anchor,
                integrity_status=integrity_status,
                integrity_check_method=INTEGRITY_CHECK_METHOD,
                corroboration_status="not_applicable",
                assertion_text=None,
                metadata={
                    "source_type": "collector_daily_brief",
                    "repo": repo["name"],
                    "branch": branch,
                    "commit_count": repo["commit_count"],
                    "diffstat": repo["diffstat"],
                    "files_touched": repo["files_touched"],
                    "commit_messages": daily_brief["commit_messages"],
                    "mode": daily_brief["mode"],
                    "window_days": window_days,
                    "integrity_check_detail": detail,
                },
            )
        )
    return units
