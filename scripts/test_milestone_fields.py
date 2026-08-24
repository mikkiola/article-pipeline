"""TDD tests for verify.py's parse_milestone_fields() -- optional
verify:/done-when: metadata attached to individual milestone checkbox
lines (B-036). Scans the whole document for checkbox lines, not just
the narrow section classify()/validate_inline_spec_structure() isolate
via isolate_milestones_section() -- that boundary serves a different
purpose (component discovery) and predates this task; extending it is
explicitly out of scope here (see B-039).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify  # noqa: E402


def write_spec(tmp_path: Path, body: str) -> Path:
    spec = tmp_path / "SPEC.md"
    spec.write_text(body, encoding="utf-8")
    return spec


def test_milestone_with_no_fields(tmp_path):
    spec = write_spec(tmp_path, "## Milestones\n\n- [ ] M1 — Do the thing\n")
    results = verify.parse_milestone_fields(str(spec))
    assert len(results) == 1
    assert results[0]["description"] == "M1 — Do the thing"
    assert results[0]["verify"] is None
    assert results[0]["done_when"] is None


def test_milestone_with_both_fields(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — Do the thing\n"
        "  verify: `pytest tests/test_foo.py::test_bar`\n"
        "  done-when: exit code 0 and output contains \"PASS\"\n",
    )
    results = verify.parse_milestone_fields(str(spec))
    assert len(results) == 1
    assert results[0]["verify"] == "`pytest tests/test_foo.py::test_bar`"
    assert results[0]["done_when"] == 'exit code 0 and output contains "PASS"'


def test_milestone_with_only_verify(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — Do the thing\n"
        "  verify: `pytest tests/test_foo.py`\n",
    )
    results = verify.parse_milestone_fields(str(spec))
    assert len(results) == 1
    assert results[0]["verify"] == "`pytest tests/test_foo.py`"
    assert results[0]["done_when"] is None


def test_milestone_with_only_done_when(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — Do the thing\n"
        "  done-when: the flag file exists\n",
    )
    results = verify.parse_milestone_fields(str(spec))
    assert len(results) == 1
    assert results[0]["verify"] is None
    assert results[0]["done_when"] == "the flag file exists"


def test_two_consecutive_milestones_no_bleed_through(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — First\n"
        "  verify: `foo`\n"
        "  done-when: bar happens\n"
        "- [ ] M2 — Second, no fields\n",
    )
    results = verify.parse_milestone_fields(str(spec))
    assert len(results) == 2
    assert results[0]["verify"] == "`foo`"
    assert results[0]["done_when"] == "bar happens"
    assert results[1]["verify"] is None
    assert results[1]["done_when"] is None


def test_verify_value_with_backticks_colons_pipes(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — Do the thing\n"
        "  verify: `pytest tests/test_foo.py::test_bar | grep PASS`\n",
    )
    results = verify.parse_milestone_fields(str(spec))
    assert len(results) == 1
    assert results[0]["verify"] == "`pytest tests/test_foo.py::test_bar | grep PASS`"


def test_non_metadata_indented_text_not_misparsed(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — Do the thing\n"
        "      This is ordinary continuation prose, indented deeper\n"
        "      than a field line, not a recognized key.\n"
        "  note: this looks like a field but isn't a recognized key\n"
        "- [ ] M2 — Second\n"
        "  verify: `real field, must still be found after M1's noise`\n",
    )
    results = verify.parse_milestone_fields(str(spec))
    assert len(results) == 2
    assert results[0]["verify"] is None
    assert results[0]["done_when"] is None
    assert results[1]["verify"] == "`real field, must still be found after M1's noise`"


def test_real_spec_after_m7_retrofit_structurally_ok():
    repo_root = Path(__file__).resolve().parent.parent
    import subprocess

    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "verify.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"verify.py exited {proc.returncode}: {proc.stderr}"

    results = verify.parse_milestone_fields(str(repo_root / "SPEC.md"))
    m7 = [r for r in results if r["description"].startswith("M7 —")]
    assert len(m7) == 1, f"expected exactly one M7 checkbox, found {len(m7)}"
    assert m7[0]["verify"] is not None
    assert m7[0]["done_when"] is not None
