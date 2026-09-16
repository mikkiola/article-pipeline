"""author/habr_weekly_author.py — the new Habr entry point (SPEC.md's
M5, "new Habr entry point script" — SPEC.md never pinned an exact
filename beyond this; this naming parallels daily_linkedin_author.py's
convention).

Consumes Collector's `manifest_*.json` (weekly) — a choice not pinned
explicitly anywhere in SPEC.md, made to match Habr's existing cadence
precedent (generate_drafts.py, the untouched v1 pipeline, is also
manifest/weekly-sourced), not to introduce a new one.

**Renders a HabrDigest (ADR-0046), not a single CanonicalStory.** An
earlier version of this module rendered one CanonicalStory under
channel_profiles.HABR_RU's structure_hint stages — replaced after a
real end-to-end run showed a typical week produces multiple included
claims, which a single 5-beat narrative can't honestly represent (see
ADR-0046's Context). One heading per included, already-vetted claim,
under a shared Russian title. Still does NOT reuse channel_author.py's
write_draft() — per SPEC.md's original Migration Sequence decision,
write_draft() hardcodes a Collector-specific title
("Как Collector (O1) считает...") with no override parameter.
Everything this module's own template text produces (title, per-
section headings) is Russian itself, per R7 — verified directly in
this module's own tests, not just the framing-derived body.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from habr_verdict_to_story import HabrDigest  # noqa: E402

_TITLE = "Еженедельная инженерная активность — проверено, не предположено"


def render_habr_digest(digest: HabrDigest) -> str:
    lines: list[str] = [f"# {_TITLE}", ""]

    for section in digest.sections:
        lines.append(f"## {section.repo}")
        lines.append("")
        lines.append(section.framing)
        lines.append("")

    return "\n".join(lines)
