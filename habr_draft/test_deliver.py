"""The Deliver job commits only what has the shape stage 2 produces."""

import hashlib
import json
import os

import pytest

from habr_draft import deliver

RUN_ID = "habr-draft-2026-10-15-101500"


def record(**over):
    base = {"run_id": RUN_ID, "observable_outcome": "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW",
            "terminal_outcome": "INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW", "failure_kind": None}
    base.update(over)
    return base


def artifact(tmp_path, rec=None, attempts=("attempt_1.md",), extra=None):
    src = tmp_path / "artifact"
    src.mkdir()
    listed = []
    for name in attempts:
        text = "# Title\n\nbody\n"
        (src / name).write_text(text, encoding="utf-8")
        listed.append({"name": name, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    if rec is not False:
        rec = rec or record()
        rec.setdefault("attempt_files", listed)
        (src / f"run_{RUN_ID}.json").write_text(json.dumps(rec), encoding="utf-8")
    for name, content in (extra or {}).items():
        (src / name).write_text(content, encoding="utf-8")
    return src


def test_valid_artifact_is_staged_into_the_run_directory_only(tmp_path):
    src = artifact(tmp_path, attempts=("attempt_1.md", "attempt_2.md"))
    dest = tmp_path / "registry" / "output" / "habr_draft" / "777"
    staged = deliver.stage(src, dest)
    assert sorted(staged) == ["attempt_1.md", "attempt_2.md", f"run_{RUN_ID}.json"]
    assert sorted(p.name for p in dest.iterdir()) == sorted(staged)
    assert sorted(p.name for p in (tmp_path / "registry").rglob("*") if p.is_file()) == sorted(staged)


def test_system_failure_and_no_eligible_topic_records_are_deliverable(tmp_path):
    src = artifact(tmp_path, rec=record(observable_outcome="NO_ELIGIBLE_TOPIC", terminal_outcome=None),
                   attempts=())
    assert deliver.stage(src, tmp_path / "d") == [f"run_{RUN_ID}.json"]


@pytest.mark.parametrize("name", [
    "notes.txt", "attempt_0.md", "attempt_1.md.bak", "run_other.json", ".hidden",
])
def test_unexpected_file_names_reject_the_whole_artifact(tmp_path, name):
    src = artifact(tmp_path, extra={name: "x"})
    dest = tmp_path / "d"
    with pytest.raises(deliver.ArtifactRejected):
        deliver.stage(src, dest)
    assert not dest.exists()  # nothing was staged


def test_subdirectory_and_symlink_are_rejected(tmp_path):
    src = artifact(tmp_path)
    (src / "state").mkdir()
    with pytest.raises(deliver.ArtifactRejected):
        deliver.validate_artifact(src)
    (src / "state").rmdir()
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")
    os.symlink(outside, src / "attempt_9.md")
    with pytest.raises(deliver.ArtifactRejected):
        deliver.validate_artifact(src)


def test_exactly_one_run_record_is_required(tmp_path):
    with pytest.raises(deliver.ArtifactRejected, match="exactly one run record"):
        deliver.validate_artifact(artifact(tmp_path, rec=False))


def test_inconsistent_or_unnamed_run_record_is_rejected(tmp_path):
    with pytest.raises(deliver.ArtifactRejected, match="inconsistent"):
        deliver.validate_artifact(artifact(
            tmp_path, rec=record(terminal_outcome="SYSTEM_FAILURE", failure_kind=None)))
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(deliver.ArtifactRejected, match="run_id"):
        deliver.validate_artifact(artifact(other, rec=record(run_id="habr-draft-2026-10-15-999999")))


def test_secret_pattern_in_any_file_rejects_the_artifact_without_echoing_it(tmp_path):
    token = "gh" + "p_" + "A" * 36
    src = artifact(tmp_path, extra={})
    (src / "attempt_1.md").write_text(f"# T\n\nTOKEN={token}\n", encoding="utf-8")
    with pytest.raises(deliver.ArtifactRejected) as raised:
        deliver.validate_artifact(src)
    assert token not in str(raised.value)


def test_staging_never_overwrites_and_collides_before_writing_anything(tmp_path):
    src = artifact(tmp_path, attempts=("attempt_1.md", "attempt_2.md"))
    dest = tmp_path / "d"
    dest.mkdir()
    (dest / "attempt_2.md").write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        deliver.stage(src, dest)
    assert [p.name for p in dest.iterdir()] == ["attempt_2.md"]  # nothing partial
    assert (dest / "attempt_2.md").read_text() == "existing"


def test_outcome_fields_must_agree(tmp_path):
    bad = record(terminal_outcome="INTERNAL_DRAFT_READY_FOR_OWNER_REVIEW",
                 observable_outcome="NO_ELIGIBLE_TOPIC")
    with pytest.raises(deliver.ArtifactRejected, match="disagrees"):
        deliver.validate_artifact(artifact(tmp_path, rec=bad))
    other = tmp_path / "o"
    other.mkdir()
    with pytest.raises(deliver.ArtifactRejected, match="unknown observable"):
        deliver.validate_artifact(artifact(other, rec=record(terminal_outcome=None,
                                                             observable_outcome="SOMETHING")))
    ok = tmp_path / "ok"
    ok.mkdir()
    deliver.validate_artifact(artifact(ok, rec=record(terminal_outcome=None,
                                                      observable_outcome="CALIBRATION_RECORDED")))


def test_attempt_files_must_match_the_record_by_name_and_hash(tmp_path):
    # an attempt file the record does not list
    src = artifact(tmp_path, rec=record(attempt_files=[]))
    with pytest.raises(deliver.ArtifactRejected, match="attempt_files"):
        deliver.validate_artifact(src)
    # a record that lists a file that is absent
    other = tmp_path / "b"
    other.mkdir()
    listed = [{"name": "attempt_1.md", "sha256": "0" * 64}]
    with pytest.raises(deliver.ArtifactRejected, match="attempt_files"):
        deliver.validate_artifact(artifact(other, rec=record(attempt_files=listed), attempts=()))
    # same name, different content
    third = tmp_path / "c"
    third.mkdir()
    with pytest.raises(deliver.ArtifactRejected, match="attempt_files"):
        deliver.validate_artifact(artifact(third, rec=record(attempt_files=listed)))


def test_trailing_newline_in_a_file_name_does_not_pass_the_name_check(tmp_path):
    src = artifact(tmp_path)
    (src / "attempt_7.md\n").write_text("x", encoding="utf-8")
    with pytest.raises(deliver.ArtifactRejected):
        deliver.validate_artifact(src)


def test_cli_exit_codes(tmp_path, capsys, monkeypatch):
    src = artifact(tmp_path)
    monkeypatch.setattr("sys.argv", ["deliver", "--artifact-dir", str(src),
                                     "--destination", str(tmp_path / "d")])
    assert deliver.main() == 0
    monkeypatch.setattr("sys.argv", ["deliver", "--artifact-dir", str(tmp_path / "missing"),
                                     "--destination", str(tmp_path / "e")])
    assert deliver.main() == 1
    assert "artifact rejected" in capsys.readouterr().err
    monkeypatch.setattr("sys.argv", ["deliver", "--artifact-dir", str(src),
                                     "--destination", str(tmp_path / "d")])
    assert deliver.main() == 1  # second delivery to the same directory: a rejection, no traceback
    assert "already holds" in capsys.readouterr().err


def test_unknown_terminal_outcome_is_not_deliverable(tmp_path):
    with pytest.raises(deliver.ArtifactRejected, match="unknown terminal_outcome"):
        deliver.validate_artifact(artifact(tmp_path, rec=record(
            terminal_outcome="PUBLISHED", observable_outcome="PUBLISHED")))
