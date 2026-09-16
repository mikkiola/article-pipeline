"""Tests for author/habr_weekly_author.py — renders a HabrDigest
(ADR-0046) into Habr-ready Markdown: one heading per included, already-
vetted claim, under a shared Russian title.

R7 check: every piece of template text this module adds (title,
per-section repo headings) must itself be Russian — asserted
explicitly, not assumed. Superseded design note: an earlier version of
this module rendered a single CanonicalStory's 5 narrative fields
under HABR_RU's structure_hint stages — replaced per ADR-0046, since
that shape can't honestly represent multiple independent claims.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from habr_verdict_to_story import HabrDigest, HabrDigestSection  # noqa: E402
from habr_weekly_author import render_habr_digest  # noqa: E402


def _cyrillic_ratio(text: str) -> float:
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 0.0
    cyrillic = [c for c in alpha if 0x0400 <= ord(c) <= 0x04FF]
    return len(cyrillic) / len(alpha)


def _section(claim_id, repo, framing):
    return HabrDigestSection(claim_id=claim_id, repo=repo, framing=framing)


def test_render_includes_every_section_not_a_subset():
    digest = HabrDigest(
        sections=[
            _section("a", "article-pipeline", "Текст про article-pipeline."),
            _section("b", "brain", "Текст про brain."),
            _section("c", "radar", "Текст про radar."),
            _section("d", "archi-kg", "Текст про archi-kg."),
            _section("e", "tooltempest", "Текст про tooltempest."),
        ]
    )
    draft = render_habr_digest(digest)
    for text in ["article-pipeline", "brain", "radar", "archi-kg", "tooltempest"]:
        assert text in draft
    for text in [
        "Текст про article-pipeline.", "Текст про brain.", "Текст про radar.",
        "Текст про archi-kg.", "Текст про tooltempest.",
    ]:
        assert text in draft


def test_render_does_not_use_channel_author_write_draft_title():
    digest = HabrDigest(sections=[_section("a", "x", "y")])
    draft = render_habr_digest(digest)
    assert "Collector (O1)" not in draft


def test_render_title_is_russian():
    # Checked separately from the per-section headings: a repo heading
    # ("## article-pipeline") legitimately contains a Latin-script repo
    # name, which would understate the title's own language on its own
    # — the title line is where "this module's own template text is
    # Russian" is actually meaningfully checkable in isolation.
    digest = HabrDigest(sections=[_section("a", "article-pipeline", "PLACEHOLDER_BODY_TEXT")])
    draft = render_habr_digest(digest)
    title_line = draft.split("\n")[0]
    assert _cyrillic_ratio(title_line) > 0.8


def test_render_template_text_overall_majority_russian():
    # Using a Cyrillic-name-friendly repo label so this checks the
    # template's overall composition without a Latin identifier
    # artificially suppressing the ratio (see test_render_title_is_russian
    # above for the isolated, identifier-free title check).
    digest = HabrDigest(sections=[_section("a", "тесты", "PLACEHOLDER_BODY_TEXT")])
    draft = render_habr_digest(digest)
    template_lines = [line for line in draft.split("\n") if line and "PLACEHOLDER_BODY_TEXT" not in line]
    template_text = " ".join(template_lines)
    assert _cyrillic_ratio(template_text) > 0.8


def test_render_single_section_digest_still_works():
    digest = HabrDigest(sections=[_section("a", "article-pipeline", "Один коммит сегодня.")])
    draft = render_habr_digest(digest)
    assert "article-pipeline" in draft
    assert "Один коммит сегодня." in draft
