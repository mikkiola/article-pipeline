"""Swappable search interface for Evidence Package (SPEC.md).

All Linkup-specific logic lives in this file. Replacing the search
vendor means rewriting this file only — the public `search()` contract
and `SearchResult` type stay the same for the driver script and any
future vendor.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from linkup import LinkupClient

BW_ITEM_NAME = "linkup-api-key-article-pipeline"


class SearchBackendError(RuntimeError):
    """Raised when the search backend cannot be configured or reached."""


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def _get_api_key() -> str:
    session = os.environ.get("BW_SESSION")
    if not session:
        raise SearchBackendError(
            "BW_SESSION is not set. Open a Bitwarden session "
            "(bw login / bw unlock) and export BW_SESSION before running."
        )
    result = subprocess.run(
        ["bw", "get", "password", BW_ITEM_NAME, "--session", session],
        capture_output=True,
        text=True,
        check=False,
    )
    key = result.stdout.strip()
    if result.returncode != 0 or not key:
        raise SearchBackendError(
            f"Failed to read '{BW_ITEM_NAME}' from Bitwarden (bw CLI exit "
            f"code {result.returncode})."
        )
    return key


_client: LinkupClient | None = None


def _get_client() -> LinkupClient:
    global _client
    if _client is None:
        _client = LinkupClient(api_key=_get_api_key())
    return _client


def search(query: str) -> list[SearchResult]:
    """Run one search request against Linkup and return text results.

    Budget accounting (max 2 calls/claim, max 20/run per SPEC.md) is
    the driver script's responsibility, not this function's — this
    function performs exactly one request per call.
    """
    client = _get_client()
    response = client.search(
        query,
        depth="standard",
        output_type="searchResults",
    )
    results: list[SearchResult] = []
    for item in response.results:
        if item.type != "text":
            continue
        results.append(SearchResult(title=item.name, url=item.url, snippet=item.content))
    return results
