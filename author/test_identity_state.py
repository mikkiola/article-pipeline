"""Tests for author/identity_state.py.

Mechanical read/write only, matching the module's own scope boundary:
no test here exercises promotion/merging semantics, because the module
doesn't implement any — see its own docstring. Style matches
linkedin_publisher/test_safety_pause.py, the closest existing precedent
for a small persisted "<component>/state/<name>.json, absent -> a named
default" module in this repository.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity_state  # noqa: E402


def test_no_identity_state_file_means_default_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(identity_state, "IDENTITY_STATE_FILE", str(tmp_path / "identity_state.json"))
    assert identity_state.load_identity_state() == identity_state.DEFAULT_IDENTITY_STATE


def test_load_identity_state_returns_persisted_content(tmp_path, monkeypatch):
    state_file = tmp_path / "identity_state.json"
    state_file.write_text(
        json.dumps({
            "core_positions": ["small fixes should land alone"],
            "emerging_positions": [],
            "recently_used": ["small fixes should land alone"],
            "underdeveloped": [],
            "open_threads": [],
            "trajectory": "moving toward smaller, more isolated changes",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(identity_state, "IDENTITY_STATE_FILE", str(state_file))
    loaded = identity_state.load_identity_state()
    assert loaded["core_positions"] == ["small fixes should land alone"]
    assert loaded["trajectory"] == "moving toward smaller, more isolated changes"


def test_write_identity_state_persists_verbatim(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    state_file = state_dir / "identity_state.json"
    monkeypatch.setattr(identity_state, "STATE_DIR", str(state_dir))
    monkeypatch.setattr(identity_state, "IDENTITY_STATE_FILE", str(state_file))
    new_state = {**identity_state.DEFAULT_IDENTITY_STATE, "trajectory": "a new trajectory"}

    path = identity_state.write_identity_state(new_state)

    assert path == str(state_file)
    written = json.loads(state_file.read_text(encoding="utf-8"))
    assert written == new_state


def test_no_recent_posts_file_means_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(identity_state, "RECENT_POSTS_FILE", str(tmp_path / "recent_posts.json"))
    assert identity_state.load_recent_posts() == []


def test_append_recent_post_creates_file_and_state_dir(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    posts_file = state_dir / "recent_posts.json"
    monkeypatch.setattr(identity_state, "STATE_DIR", str(state_dir))
    monkeypatch.setattr(identity_state, "RECENT_POSTS_FILE", str(posts_file))

    identity_state.append_recent_post("First real published post.")

    assert json.loads(posts_file.read_text(encoding="utf-8")) == ["First real published post."]


def test_append_recent_post_truncates_to_the_limit_oldest_dropped_first(tmp_path, monkeypatch):
    posts_file = tmp_path / "recent_posts.json"
    monkeypatch.setattr(identity_state, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(identity_state, "RECENT_POSTS_FILE", str(posts_file))
    monkeypatch.setattr(identity_state, "RECENT_POSTS_LIMIT", 3)

    for i in range(1, 5):
        identity_state.append_recent_post(f"post {i}")

    assert identity_state.load_recent_posts() == ["post 2", "post 3", "post 4"]
