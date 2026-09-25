"""Collector's ACL adapter — Collector manifest_*.json/daily_brief_*.json
-> list[CanonicalUnit] (SPEC.md's source-independence extension,
Milestone M3, Part 1).

Read-only against Collector, same convention as author/source_adapter.py:
reads JSON already on disk and (for the integrity check) makes read-only
GitHub REST API calls — never writes to Collector's own repository or
scripts, and never consults a local checkout of any scanned repository.

Every unit this adapter produces has corroboration_status=
"not_applicable" — Collector's raw telemetry (a commit happened, a
file was touched) makes no falsifiable assertion to corroborate.
Derived-claim synthesis (e.g. "activity increased this week") is out
of scope (SPEC.md's Out of Scope section) — every raw record passes
through as its own individual unit, unsynthesized.

**Ancestry check, one shared code path for both record types**
(docs/adr/0056-*.md): Collector records, for every repo it scans, the
branch and the exact tip commit SHA (`head_sha`) it saw at scan time. The
check asks GitHub whether that SHA is the branch's current tip or one of
its ancestors — GET /repos/{owner}/{repo}/compare/{head_sha}...{branch},
valid iff behind_by == 0 (status "identical" or "ahead"). Labeled
`integrity_check_method="ancestry_reconciliation"`. It confirms the
repository, the branch and that SHA are real and related; it does NOT
confirm how many commits happened in the window (a zero-commit repo
verifies exactly as strongly as a busy one) and does not verify
individual commit messages. Stated plainly so the label isn't read as
more than it is.

**Attribution.** A daily brief (schema_version 2) attributes each commit
message to its repository. Each unit receives only its own repository's
messages, never the brief-wide list — an excluded unit's messages can
therefore never reach the post prompt through an included unit.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from os import environ
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contract import CanonicalUnit  # noqa: E402

INTEGRITY_CHECK_METHOD = "ancestry_reconciliation"

# The only daily_brief schema this adapter understands (Collector's
# daily_brief.py SCHEMA_VERSION). An unknown version is never guessed at:
# every unit built from it is marked invalid.
DAILY_BRIEF_SCHEMA_VERSION = 2

GITHUB_API_BASE = "https://api.github.com"
GITHUB_OWNER = "mikkiola"
# Collector's `name` is the checkout DIRECTORY name. Two directories can be
# the same GitHub repository on different branches (radar-vault is the
# `vault` branch of mikkiola/radar). Applied to the API call only, nowhere
# else.
GITHUB_REPO_FOR_DIRECTORY = {"radar-vault": "radar"}
# Deliberately not GH_TOKEN/GITHUB_TOKEN: the gh CLI (used by
# daily_linkedin_author._check_repo_visibility) reads those, and enabling it
# there would change the post prompt's public-link behavior as a side effect.
TOKEN_ENV = "GITHUB_APP_TOKEN"
GITHUB_TIMEOUT_SECONDS = 15

# Anti-"junk drawer" safeguard (ADR-0045): the exact set of metadata
# keys each source_type is allowed to produce. A future adapter (e.g.
# Brain's, not built this sprint) adds its own entry here, not a new
# mechanism. check_metadata_whitelist() below is the enforcement point.
METADATA_WHITELIST = {
    "collector_manifest": {
        "source_type",
        "repo",
        "branch",
        "head_sha",
        "commit_count",
        "counts",
        "window_days",
        "integrity_check_detail",
    },
    "collector_daily_brief": {
        "source_type",
        "repo",
        "branch",
        "head_sha",
        "commit_count",
        "diffstat",
        "files_touched",
        "commit_messages",
        "mode",
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

def _github_get(path: str, token: str) -> tuple[int, dict | None]:
    """One authenticated, read-only GET against the GitHub REST API.
    Returns (http_status, parsed_json_body_or_None). Network-level failures
    (DNS, timeout, connection reset) propagate as exceptions — the caller
    (check_integrity) treats any exception as fail-closed."""
    request = urllib.request.Request(
        GITHUB_API_BASE + path,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "article-pipeline-collector-adapter",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=GITHUB_TIMEOUT_SECONDS) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, None


def check_integrity(repo_name: str, branch: str | None, head_sha: str | None) -> tuple[str, str]:
    """Returns (integrity_status, detail) for one repo record.

    Asks GitHub whether `head_sha` — the branch tip Collector recorded at
    scan time — is the current tip of `branch`, or one of its ancestors:
    GET /repos/{owner}/{repo}/compare/{head_sha}...{branch}. Valid iff the
    response has behind_by == 0 (status "identical", or "ahead" when the
    branch has moved on since the scan). Invalid for "behind", "diverged"
    (the SHA lives on some other branch), 404 (SHA, repo or branch does not
    exist — GitHub answers all three the same way), any other HTTP status
    (e.g. 403 when the token cannot see the repo, or a rate limit), any
    request failure, a missing token, or a record with no head_sha/branch.
    Fail closed everywhere; there is no fallback to a local checkout.

    Compared against the SHA Collector actually observed, not against
    whatever HEAD is later: exact match, no tolerance.
    """
    if not head_sha:
        return "invalid", (
            f"no head_sha recorded for {repo_name!r} (a record written before "
            f"Collector began recording it, or Collector could not resolve HEAD)"
        )
    if not branch:
        return "invalid", f"no branch recorded for {repo_name!r}; cannot verify head_sha"

    token = environ.get(TOKEN_ENV)
    if not token:
        return "invalid", f"{TOKEN_ENV} is not set; cannot verify {repo_name!r} against GitHub"

    github_repo = GITHUB_REPO_FOR_DIRECTORY.get(repo_name, repo_name)
    path = (
        f"/repos/{GITHUB_OWNER}/{github_repo}/compare/"
        f"{urllib.parse.quote(head_sha, safe='')}...{urllib.parse.quote(branch, safe='/')}"
        f"?per_page=1"
    )
    try:
        http_status, body = _github_get(path, token)
    except Exception as error:  # noqa: BLE001 — any failure to verify is invalid
        return "invalid", f"GitHub API request failed for {github_repo}@{branch}: {error}"

    if http_status == 404:
        return "invalid", (
            f"GitHub API returned 404 for {github_repo}@{branch} at {head_sha[:12]}: "
            f"the repository, the branch or the commit does not exist (or the token cannot see it)"
        )
    if http_status != 200 or body is None:
        return "invalid", f"GitHub API returned HTTP {http_status} for {github_repo}@{branch}"

    compare_status = body.get("status")
    if body.get("behind_by") == 0 and compare_status in ("identical", "ahead"):
        return "valid", (
            f"head_sha {head_sha[:12]} is on {github_repo}@{branch} "
            f"(compare status={compare_status}, ahead_by={body.get('ahead_by')})"
        )
    return "invalid", (
        f"head_sha {head_sha[:12]} is not an ancestor of {github_repo}@{branch} "
        f"(compare status={compare_status}, behind_by={body.get('behind_by')})"
    )


def adapt_manifest(manifest: dict) -> list[CanonicalUnit]:
    """Builds one CanonicalUnit per repo entry in a Collector
    manifest_*.json. `branch` and `head_sha` both come from the manifest;
    a manifest written before Collector recorded head_sha has none, and
    its units are marked invalid (fail closed), not guessed at."""
    scan_timestamp = datetime.fromisoformat(manifest["scan_timestamp"])
    window_days = manifest["window_days"]

    units = []
    for repo in manifest["repos"]:
        integrity_status, detail = check_integrity(
            repo["name"], repo.get("branch"), repo.get("head_sha")
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
                    "branch": repo.get("branch"),
                    "head_sha": repo.get("head_sha"),
                    "commit_count": repo["commit_count"],
                    "counts": repo.get("counts"),
                    "window_days": window_days,
                    "integrity_check_detail": detail,
                },
            )
        )
    return units


def _messages_by_repo(commit_messages: list) -> dict[str, list[str]]:
    """Groups a schema-2 brief's attributed commit_messages by repo,
    keeping only the subject text. A malformed entry raises: an unattributable
    message must never be guessed into some repo's slice."""
    by_repo: dict[str, list[str]] = {}
    for entry in commit_messages:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("repo"), str)
            or not isinstance(entry.get("subject"), str)
        ):
            raise ValueError(
                f"commit_messages entry is not a {{repo, sha, subject}} object: {entry!r}"
            )
        by_repo.setdefault(entry["repo"], []).append(entry["subject"])
    return by_repo


def adapt_daily_brief(daily_brief: dict) -> list[CanonicalUnit]:
    """Builds one CanonicalUnit per repo entry in a Collector
    daily_brief_<date>.json (schema_version 2).

    A brief whose schema_version is not DAILY_BRIEF_SCHEMA_VERSION (notably
    every brief written before the field existed) is not interpreted: each
    unit is built invalid with an empty message slice and no API call is
    made.

    Each unit carries only ITS OWN repository's commit subjects, taken from
    the brief's attributed `commit_messages`; never the brief-wide list.

    One documented approximation remains: daily_brief carries only a date
    token, not the scan instant, so `created_at` is that date's 23:59:59
    UTC. It is not used by the integrity check (which compares head_sha, not
    a time window).
    """
    anchor = datetime.fromisoformat(daily_brief["date"]).replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc
    )
    schema_version = daily_brief.get("schema_version")
    supported = schema_version == DAILY_BRIEF_SCHEMA_VERSION
    messages_by_repo = _messages_by_repo(daily_brief["commit_messages"]) if supported else {}

    units = []
    for repo in daily_brief["per_repo"]:
        branch = repo.get("branch")
        head_sha = repo.get("head_sha")
        if supported:
            integrity_status, detail = check_integrity(repo["name"], branch, head_sha)
        else:
            integrity_status, detail = "invalid", (
                f"daily_brief schema_version={schema_version!r}, expected "
                f"{DAILY_BRIEF_SCHEMA_VERSION}; record not interpreted"
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
                    "head_sha": head_sha,
                    "commit_count": repo["commit_count"],
                    "diffstat": repo["diffstat"],
                    "files_touched": repo["files_touched"],
                    "commit_messages": messages_by_repo.get(repo["name"], []),
                    "mode": daily_brief["mode"],
                    "integrity_check_detail": detail,
                },
            )
        )
    return units
