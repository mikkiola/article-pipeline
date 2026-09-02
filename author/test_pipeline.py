#!/usr/bin/env python3
"""Plain-assert tests for the Author MVP pilot pipeline.

Run: python3 test_pipeline.py

Matches Collector's own test convention (plain asserts, no framework)
rather than this repo's usual pytest style — deliberate, per the task
that asked for this pipeline.
"""

import re

from source_adapter import adapt_collector_manifest
from story_builder import build_story
from channel_author import write_draft
from channel_profiles import HABR_RU, LINKEDIN_EN

SAMPLE_MANIFEST = {
    "scan_timestamp": "2026-09-01T07:56:02.716151+00:00",
    "window_days": 7,
    "counts_total": {"value": 5, "explicit_service": 2, "default_service": 1},
    "repos": [
        {
            "name": "collector",
            "branch": "main",
            "commit_count": 3,
            "counts": {"value": 2, "explicit_service": 1, "default_service": 0},
        },
        {
            "name": "other-repo",
            "branch": "main",
            "commit_count": 5,
            "counts": {"value": 3, "explicit_service": 1, "default_service": 1},
        },
    ],
    "value_files": [
        {"repo": "collector", "path": "scripts/classify.py", "classification": "value",
         "matched_rule": "brain/**", "external_value": "unknown"},
        {"repo": "collector", "path": "scripts/tier0_scan.py", "classification": "value",
         "matched_rule": "brain/**", "external_value": "unknown"},
        {"repo": "other-repo", "path": "docs/adr/0001-x.md", "classification": "value",
         "matched_rule": "docs/adr/** (any repo)", "external_value": "unknown"},
    ],
}


def test_adapter_facts_and_evidence_trace_to_input_manifest():
    event = adapt_collector_manifest(SAMPLE_MANIFEST, repo_filter="collector")

    # Every evidence record must be one of the actual collector value_files.
    input_collector_paths = {
        vf["path"] for vf in SAMPLE_MANIFEST["value_files"] if vf["repo"] == "collector"
    }
    output_paths = {e["path"] for e in event.evidence}
    assert output_paths == input_collector_paths, (
        f"evidence paths {output_paths} must exactly match input collector "
        f"value_files {input_collector_paths} — no more, no fewer"
    )
    assert all(e["repo"] == "collector" for e in event.evidence), (
        "no non-collector evidence should leak in when repo_filter='collector'"
    )

    # Every fact's numbers must match the real input manifest fields.
    commit_fact = next(f for f in event.facts if f["type"] == "repo_commit_count")
    assert commit_fact["commit_count"] == 3, "must trace to the real manifest repo entry, not invented"

    class_fact = next(f for f in event.facts if f["type"] == "repo_classification_counts")
    assert class_fact == {
        "type": "repo_classification_counts", "repo": "collector",
        "value": 2, "explicit_service": 1, "default_service": 0,
    }

    totals_fact = next(f for f in event.facts if f["type"] == "workspace_totals")
    assert totals_fact["value"] == SAMPLE_MANIFEST["counts_total"]["value"]
    assert totals_fact["explicit_service"] == SAMPLE_MANIFEST["counts_total"]["explicit_service"]
    assert totals_fact["default_service"] == SAMPLE_MANIFEST["counts_total"]["default_service"]


def test_adapter_evidence_is_empty_when_repo_has_no_value_files():
    event = adapt_collector_manifest(SAMPLE_MANIFEST, repo_filter="other-repo")
    # other-repo has exactly one value_file in the sample — sanity check
    # the filter isn't accidentally including collector's.
    assert len(event.evidence) == 1
    assert event.evidence[0]["path"] == "docs/adr/0001-x.md"


def test_story_evidence_refs_are_valid_indices_into_event_evidence():
    event = adapt_collector_manifest(SAMPLE_MANIFEST, repo_filter="collector")
    story = build_story(event)

    assert all(0 <= ref < len(event.evidence) for ref in story.evidence_refs), (
        f"evidence_refs {story.evidence_refs} must all be valid indices into "
        f"an evidence list of length {len(event.evidence)}"
    )
    # With 2 real evidence entries, evidence_refs must reference exactly
    # those 2 positions — not fewer (dropped), not more (fabricated).
    assert sorted(story.evidence_refs) == list(range(len(event.evidence)))


def test_story_evidence_refs_empty_when_event_evidence_empty():
    # Real production case: collector had zero value-classified files in
    # the actual 2026-09-01 manifest snapshot.
    empty_manifest = dict(SAMPLE_MANIFEST)
    empty_manifest["value_files"] = []
    event = adapt_collector_manifest(empty_manifest, repo_filter="collector")
    assert event.evidence == []
    story = build_story(event)
    assert story.evidence_refs == [], "no evidence available means no refs — never fabricate one"


def test_habr_and_linkedin_drafts_differ_in_structure_not_just_language():
    event = adapt_collector_manifest(SAMPLE_MANIFEST, repo_filter="collector")
    story = build_story(event)

    habr = write_draft(story, HABR_RU)
    linkedin = write_draft(story, LINKEDIN_EN)

    habr_headings = re.findall(r"^## (.+)$", habr, flags=re.MULTILINE)
    linkedin_headings = re.findall(r"^## (.+)$", linkedin, flags=re.MULTILINE)

    assert habr_headings != linkedin_headings, "channel drafts must not share identical heading structure"

    # Habr's structure_hint has 4 stages + a "high" evidence_density
    # section = 5 headings; LinkedIn's has 4 stages + "medium" density
    # (no extra evidence section) = 4 headings — genuinely different
    # section counts, not just translated labels for the same shape.
    assert len(habr_headings) == 5, habr_headings
    assert len(linkedin_headings) == 4, linkedin_headings

    # Confirm the same story content (core_problem) appears under a
    # differently-labeled, differently-positioned heading in each.
    assert habr_headings[0] == "Проблема"
    assert linkedin_headings[0] == "Context"
    assert story.core_problem in habr
    assert story.core_problem in linkedin

    # The actual regression this fix targets: no two headings within
    # the SAME draft should render identical body text. Splitting on
    # "## " gives one chunk per section; the first line of each chunk
    # is the heading, the rest is its body.
    def _section_bodies(draft: str) -> list[str]:
        chunks = draft.split("\n## ")[1:]  # drop the H1 title chunk
        return ["\n".join(chunk.split("\n")[1:]).strip() for chunk in chunks]

    for draft_name, draft in (("habr", habr), ("linkedin", linkedin)):
        bodies = _section_bodies(draft)
        non_empty_bodies = [b for b in bodies if b]
        assert len(non_empty_bodies) == len(set(non_empty_bodies)), (
            f"{draft_name} draft has two sections with identical body "
            f"text — the stage-to-field mapping is reusing one "
            f"CanonicalStory field under two different headings"
        )


if __name__ == "__main__":
    tests = [
        test_adapter_facts_and_evidence_trace_to_input_manifest,
        test_adapter_evidence_is_empty_when_repo_has_no_value_files,
        test_story_evidence_refs_are_valid_indices_into_event_evidence,
        test_story_evidence_refs_empty_when_event_evidence_empty,
        test_habr_and_linkedin_drafts_differ_in_structure_not_just_language,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {test.__name__}: {e}")

    print()
    if failures:
        print(f"{failures}/{len(tests)} test(s) FAILED")
        raise SystemExit(1)
    else:
        print(f"All {len(tests)} test(s) passed")
