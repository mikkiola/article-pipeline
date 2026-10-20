"""Code-fragment retrieval for the Habr draft path (SPEC.md M9 requirement 43).

Fragments come from ONE specific commit SHA each (never a branch tip), through
the existing GitHub client path (`collector._github_get`, `TOKEN_ENV`). A
fragment is excluded, with a recorded reason, when it has no patch, sits on a
denylisted path, matches a secret pattern, or its commit's author is not an
owner identity.

Outcomes are kept distinct (requirement: technical fetch errors are not
"no eligible topic"): `FetchResult.errors` holds technical failures,
`FetchResult.exclusions` holds content/policy exclusions.
"""

from __future__ import annotations

import fnmatch
import hashlib
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "strategy_layer" / "adapters"))

from habr_draft import secret_scan  # noqa: E402
from habr_draft.config import HabrConfig  # noqa: E402

DENYLIST_GLOBS = (
    "*.lock", "package-lock.json", "yarn.lock", "poetry.lock", "uv.lock", "Pipfile.lock",
    "*.min.js", "*.min.css", "*.map", "*.pyc",
    "dist/*", "build/*", "output/*", "*/output/*", "*__pycache__/*", "node_modules/*",
    ".env", ".env.*", "*/.env", "*/.env.*", "*.pem", "*.key", "*.p12", "*.pfx",
)


def is_denylisted(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in DENYLIST_GLOBS)


# ------------------------------------------------------------ authorship
#
# Admission rule (ADR-0070 point 3): a fragment is usable when the commit's
# AUTHOR is an owner identity. It is a content-admission check of this internal
# pipeline, not a sole-authorship claim and not a legal determination. The
# committer and the commit message (trailers) are deliberately not read: all
# three allow-listed repositories have exactly one account with write access
# (the owner), so the one way a third party's commit can reach `main` is the
# owner merging it, and a merge keeps the original author.


class MalformedCommit(ValueError):
    """The commit response does not have the shape the admission rule reads.
    `field` names the offending field, never its content. A commit that raises
    this is never admitted: it is recorded as a technical error."""

    def __init__(self, field: str) -> None:
        super().__init__(field)
        self.field = field


def _normalize_email(email: str | None) -> str:
    """One normalisation for every address comparison: surrounding whitespace
    removed, case folded. None -> ""."""
    return email.strip().lower() if isinstance(email, str) else ""


def _as_dict(value: object, field: str) -> dict:
    """None (absent / null in the API response) -> {}; anything else that is
    not an object is malformed."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise MalformedCommit(field)
    return value


def _as_optional_str(container: dict, key: str, field: str) -> str | None:
    value = container.get(key)
    if value is not None and not isinstance(value, str):
        raise MalformedCommit(field)
    return value


def authorship_exclusion(commit: dict, owner_identities: list[dict]) -> str | None:
    """Returns an exclusion reason, or None when the commit's author is an owner
    identity. A display name never establishes the owner: `name` is free text.
    The owner is established by a GitHub login or an address only.

    Raises `MalformedCommit` when the author fields have the wrong type."""
    if not isinstance(commit, dict):
        raise MalformedCommit("commit_response")
    git_author = _as_dict(_as_dict(commit.get("commit"), "commit").get("author"), "commit.author")
    api_author = _as_dict(commit.get("author"), "author")
    if not (git_author or api_author):
        return "authorship_unknown"
    login = _as_optional_str(api_author, "login", "author.login")
    address = _normalize_email(_as_optional_str(git_author, "email", "commit.author.email"))
    for owner in owner_identities:
        if login and owner.get("login") and login == owner["login"]:
            return None
        if address and address == _normalize_email(owner.get("email")):
            return None
    return "author_not_owner"


# ----------------------------------------------------------------- fetch


@dataclass
class FetchResult:
    fragments: list[dict] = field(default_factory=list)
    exclusions: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def _commit_files(body: dict) -> list[dict]:
    """The commit's file entries, validated before any fragment is built."""
    files = body.get("files")
    if files is None:
        return []
    if not isinstance(files, list):
        raise MalformedCommit("files")
    for file in files:
        if not isinstance(file, dict):
            raise MalformedCommit("files[]")
        filename = file.get("filename")
        if not isinstance(filename, str) or not filename:
            raise MalformedCommit("files[].filename")
        patch = file.get("patch")
        if patch is not None and not isinstance(patch, str):
            raise MalformedCommit("files[].patch")
    return files


def fetch_fragments(
    repo: str,
    commits: list[dict],
    token: str | None,
    config: HabrConfig,
    *,
    get: Callable[[str, str], tuple[int, dict | None]] | None = None,
    patterns: dict | None = None,
) -> FetchResult:
    """`commits` are {sha, subject} entries of the candidate repository.
    Never raises on a technical GitHub failure: it is recorded in `errors`."""
    import collector

    getter = get or collector._github_get
    github_repo = collector.GITHUB_REPO_FOR_DIRECTORY.get(repo, repo)
    patterns = patterns if patterns is not None else secret_scan.load_patterns()
    result = FetchResult()
    if not token:
        result.errors.append({"repo": repo, "kind": "token_missing"})
        return result

    counter = 0
    for entry in commits:
        sha = entry["sha"]
        path = (
            f"/repos/{collector.GITHUB_OWNER}/{github_repo}/commits/"
            f"{urllib.parse.quote(sha, safe='')}"
        )
        try:
            status, body = getter(path, token)
        except Exception as error:  # noqa: BLE001 - recorded, never fatal here
            result.errors.append({"repo": repo, "sha": sha, "kind": "network", "error_class": type(error).__name__})
            continue
        if status != 200 or not isinstance(body, dict):
            result.errors.append({"repo": repo, "sha": sha, "kind": "http", "status": status})
            continue
        try:
            authorship = authorship_exclusion(body, config.owner_identities)
            files = _commit_files(body)
        except MalformedCommit as error:
            result.errors.append({"repo": repo, "sha": sha, "kind": "malformed_commit", "field": error.field})
            continue
        for file in files:
            file_path = file.get("filename", "")
            patch = file.get("patch")
            base = {"repo": repo, "sha": sha, "path": file_path}
            if not isinstance(patch, str) or not patch:
                result.exclusions.append({**base, "reason": "no_patch"})
                continue
            if is_denylisted(file_path):
                result.exclusions.append({**base, "reason": "denylisted_path"})
                continue
            hits = secret_scan.scan(patch, patterns)
            if hits:
                result.exclusions.append({**base, "reason": "secret_pattern", "patterns": hits})
                continue
            if authorship:
                result.exclusions.append({**base, "reason": f"authorship:{authorship}"})
                continue
            counter += 1
            result.fragments.append(
                {
                    "id": f"{repo}:frag_{counter:02d}",
                    "repo": repo,
                    "sha": sha,
                    "path": file_path,
                    "content": patch,
                    "content_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
                }
            )
    return result


def select_within_cap(fragments: list[dict], cap_chars: int) -> tuple[list[dict], list[dict]]:
    """Deterministic, in order: fragments are added while the cumulative
    content size stays within `cap_chars`. Returns (kept, dropped)."""
    kept: list[dict] = []
    dropped: list[dict] = []
    used = 0
    for fragment in fragments:
        size = len(fragment["content"])
        if used + size <= cap_chars:
            kept.append(fragment)
            used += size
        else:
            dropped.append({"id": fragment["id"], "reason": "volume_cap"})
    return kept, dropped


# ------------------------------------------------------------ visibility


def repo_visibility(
    repo: str,
    token: str | None,
    get: Callable[[str, str], tuple[int, dict | None]] | None = None,
) -> bool | None:
    """Live public-repository check through the same GitHub reader and token
    as the fragment fetch. True = confirmed public, False = confirmed not
    public, None = the check could not be completed (missing token, request
    failure, any status other than 200). It does not need the `gh` CLI or a
    second token in the environment, and it never conflates "could not check"
    with "not public"."""
    import collector

    if not token:
        return None
    getter = get or collector._github_get
    github_repo = collector.GITHUB_REPO_FOR_DIRECTORY.get(repo, repo)
    try:
        status, body = getter(f"/repos/{collector.GITHUB_OWNER}/{github_repo}", token)
    except Exception:  # noqa: BLE001 - reported as "could not check"
        return None
    if status != 200 or not isinstance(body, dict):
        return None
    private = body.get("private")
    if private is False:
        return True
    if private is True:
        return False
    return None
