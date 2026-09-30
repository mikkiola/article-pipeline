"""Identity continuity state for fact-mode generation (ADR-0059 Decision
point 6): the author's real recent published posts and a compact,
persisted `identity_state`, both passed into `_build_fact_prompt()` as
generation-time context — nothing else.

Read/write only — this module does not decide WHAT `identity_state`'s
content should become after a post. ADR-0059 requires a position never
be promoted from `emerging_positions` to `core_positions` on a single
post, equivalent positions be merged rather than duplicated, and the
whole state stay compact. Computing that update requires interpreting
what a given post's PERSONAL POSITION actually was — that lives only in
the `reasoning` object (`daily_linkedin_author.REASONING_REQUIRED_KEYS`)
or the published post text itself, and deriving an update from either is
explicitly out of this module's scope (see `docs/BACKLOG.md`'s `[B-070]`
for the deferred reasoning-persistence/aggregation question this
connects to, and this module's own `write_identity_state()` docstring).
`write_identity_state()` below is a mechanical persist-what-you're-given
function; nothing in this repository today decides what to give it.

Two separate files, matching `linkedin_publisher/safety_pause.py`'s
existing "`<component>/state/<name>_state.json`, absent -> a named
default" convention — a single compact mutable state, not an
Immutable-Lineage per-event record like `publication_registry/output/`:
- `state/identity_state.json` — the compact `identity_state` object
  itself, in ADR-0059 Decision point 6's described shape.
- `state/recent_posts.json` — a small, capped list of real published
  post texts, the "author's real recent published posts" ADR-0059 also
  requires as generation input. No repository precedent stores real
  post text anywhere else: `publication_registry.contract.
  PublicationRecord` stores only `url` (confirmed by direct read, out
  of scope to change here), and no LinkedIn read-API integration exists
  in `linkedin_client.py` today (`publish_post()` only) to re-fetch a
  live post's text after the fact. This file is therefore this task's
  own, newly introduced persistence point for that text — appended to
  at the same place `daily_publish.py` already holds a freshly
  published post's text in memory, right after a successful publish.
"""

from __future__ import annotations

import json
import os

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
IDENTITY_STATE_FILE = os.path.join(STATE_DIR, "identity_state.json")
RECENT_POSTS_FILE = os.path.join(STATE_DIR, "recent_posts.json")

# Plain implementation default (a buffer size), not an owner-set policy
# threshold in the sense SPEC.md's PatternCandidate.threshold is — no
# ADR or SPEC text names a required count of "recent" posts to keep.
RECENT_POSTS_LIMIT = 5

DEFAULT_IDENTITY_STATE = {
    "core_positions": [],
    "emerging_positions": [],
    "recently_used": [],
    "underdeveloped": [],
    "open_threads": [],
    "trajectory": "",
}


def load_identity_state() -> dict:
    """Returns the persisted `identity_state`, or ADR-0059 Decision
    point 6's described-but-empty shape if no state file exists yet
    (e.g. the very first fact-mode run under this contract) — the same
    "absent -> a named default, never invented content" precedent
    `linkedin_publisher/safety_pause.py`'s `check_safety_pause_state()`
    already establishes in this project."""
    if not os.path.exists(IDENTITY_STATE_FILE):
        return dict(DEFAULT_IDENTITY_STATE)
    with open(IDENTITY_STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def write_identity_state(state: dict) -> str:
    """Persists `state` verbatim. Deciding what the next `identity_state`
    should contain (promotion, merging, trajectory updates) is not
    performed here, or anywhere in this repository today — see this
    module's own docstring."""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(IDENTITY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return IDENTITY_STATE_FILE


def load_recent_posts() -> list[str]:
    """Returns the persisted list of real recent post texts, oldest
    first, or an empty list if none exist yet (first run)."""
    if not os.path.exists(RECENT_POSTS_FILE):
        return []
    with open(RECENT_POSTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def append_recent_post(post_text: str) -> str:
    """Appends a genuinely-published post's real text and truncates to
    the last RECENT_POSTS_LIMIT entries, oldest dropped first. Call
    only once a real LinkedIn publish has actually succeeded — never
    for a gate-blocked or unpublished draft — so every stored entry is
    a real published post, matching ADR-0059's own wording."""
    posts = load_recent_posts()
    posts.append(post_text)
    posts = posts[-RECENT_POSTS_LIMIT:]
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(RECENT_POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return RECENT_POSTS_FILE
