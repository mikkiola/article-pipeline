"""TDD tests for verify.py's check_milestones_boundary_integrity() --
a lint backstop for the [B-039] bug class (a milestone-detail section
written at the "## " level truncates isolate_milestones_section()'s
own output early, silently hiding later checkbox lines).

Why this check does NOT literally "scan isolate_milestones_section()'s
output for a ## heading": that output can never contain one by
construction -- the function is defined to stop exactly at the first
"## " heading it finds, so any such heading is already excluded from
what it returns. A check limited to that output would always pass,
regardless of whether the bug is present. The actual, detectable
signature of this bug class is a whole-document checkbox count
exceeding the isolated section's own checkbox count: checkboxes exist
somewhere in the document but outside the boundary
isolate_milestones_section() recognizes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify  # noqa: E402


def write_spec(tmp_path: Path, body: str) -> Path:
    spec = tmp_path / "SPEC.md"
    spec.write_text(body, encoding="utf-8")
    return spec


def test_detects_checkbox_truncated_by_interior_h2_heading(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — First\n\n"
        "## M2 — Detail (wrong level, reproduces B-039's original bug)\n\n"
        "- [ ] M2 — Second, orphaned outside the isolated section\n",
    )
    result = verify.check_milestones_boundary_integrity(str(spec))
    assert result["status"] == "VIOLATION"
    assert result["isolated_count"] == 1
    assert result["total_count"] == 2


def test_correctly_nested_h3_detail_section_is_ok(tmp_path):
    spec = write_spec(
        tmp_path,
        "## Milestones\n\n"
        "- [ ] M1 — First\n\n"
        "### M2 — Detail (correct level, nests under Milestones)\n\n"
        "- [ ] M2 — Second, correctly captured\n",
    )
    result = verify.check_milestones_boundary_integrity(str(spec))
    assert result["status"] == "OK"
    assert result["isolated_count"] == 2
    assert result["total_count"] == 2


def test_no_milestones_section_at_all(tmp_path):
    spec = write_spec(tmp_path, "# Just a title\n\nNo milestones here.\n")
    result = verify.check_milestones_boundary_integrity(str(spec))
    assert result["status"] == "OK"
    assert result["isolated_count"] == 0
    assert result["total_count"] == 0


def test_real_spec_after_heading_demotion_fix_is_ok():
    repo_root = Path(__file__).resolve().parent.parent
    result = verify.check_milestones_boundary_integrity(str(repo_root / "SPEC.md"))
    assert result["status"] == "OK", result
    assert result["isolated_count"] == 7
    assert result["total_count"] == 7
