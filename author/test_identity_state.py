"""Tests for author/identity_state.py.

Mechanical read/write only, matching the module's own scope boundary:
no test here exercises promotion/merging semantics, because the module
doesn't implement any — see its own docstring. Style matches
linkedin_publisher/test_safety_pause.py, the closest existing precedent
for a small persisted "<component>/state/<name>.json, absent -> a named
default" module in this repository.
"""

import importlib.util
import json
import os
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


# --- AUTHOR_STATE_DIR: STATE_DIR is read from the env at import time ---
#
# Each case loads a fresh, separately named copy of identity_state.py
# (same approach as publication_registry/test_writer.py's REGISTRY_OUTPUT_DIR
# cases) so the shared `identity_state` module other tests monkeypatch is
# left untouched.

_DEFAULT_STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(identity_state.__file__)), "state")


def _load_identity_state_copy():
    spec = importlib.util.spec_from_file_location("identity_state_state_dir_probe", identity_state.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_dir_uses_author_state_dir_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTHOR_STATE_DIR", str(tmp_path / "registry" / "state"))
    probe = _load_identity_state_copy()
    assert probe.STATE_DIR == str(tmp_path / "registry" / "state")
    assert probe.IDENTITY_STATE_FILE == str(tmp_path / "registry" / "state" / "identity_state.json")
    assert probe.RECENT_POSTS_FILE == str(tmp_path / "registry" / "state" / "recent_posts.json")


def test_state_dir_defaults_when_author_state_dir_unset(monkeypatch):
    monkeypatch.delenv("AUTHOR_STATE_DIR", raising=False)
    assert _load_identity_state_copy().STATE_DIR == _DEFAULT_STATE_DIR


def test_state_dir_defaults_when_author_state_dir_empty(monkeypatch):
    monkeypatch.setenv("AUTHOR_STATE_DIR", "")
    assert _load_identity_state_copy().STATE_DIR == _DEFAULT_STATE_DIR


def test_first_run_under_env_override_with_no_state_dir_returns_defaults(monkeypatch, tmp_path):
    """Invariant: a checkout with no prior committed state behaves exactly
    as before — empty list, default shape, no crash — even though the
    override directory does not exist yet."""
    state_dir = tmp_path / "registry" / "state"
    monkeypatch.setenv("AUTHOR_STATE_DIR", str(state_dir))
    probe = _load_identity_state_copy()

    assert probe.load_recent_posts() == []
    assert probe.load_identity_state() == probe.DEFAULT_IDENTITY_STATE
    assert not state_dir.exists()


def test_writes_under_env_override_create_a_missing_state_dir_and_carry_over(monkeypatch, tmp_path):
    """Invariant: the write path succeeds on a checkout where the state
    directory does not exist yet, and a later process pointed at the same
    directory reads back what an earlier one wrote."""
    state_dir = tmp_path / "registry" / "state"
    monkeypatch.setenv("AUTHOR_STATE_DIR", str(state_dir))

    first_run = _load_identity_state_copy()
    assert not state_dir.exists()
    first_run.append_recent_post("post from run 1")
    first_run.write_identity_state({**first_run.DEFAULT_IDENTITY_STATE, "trajectory": "t1"})
    assert state_dir.is_dir()

    second_run = _load_identity_state_copy()
    assert second_run.load_recent_posts() == ["post from run 1"]
    assert second_run.load_identity_state()["trajectory"] == "t1"
    second_run.append_recent_post("post from run 2")
    assert second_run.load_recent_posts() == ["post from run 1", "post from run 2"]
