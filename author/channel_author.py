"""Stage 4: Channel Author — (CanonicalStory, ChannelProfile) -> Markdown.

Takes the SAME CanonicalStory for every channel — no channel-specific
interpretation happens here or upstream in Story Builder/Source
Adapter, only channel-specific *presentation* (section order, heading
language, and how much of the story's own text each section repeats).

Plain string templating, no LLM call — a first, inspectable prototype
the owner is expected to hand-edit, not a final automated pipeline.
Translating the canonical (English) story content into actual Russian
prose for Habr is NOT done here — see the report's placeholder list.
"""

from story_builder import CanonicalStory
from channel_profiles import ChannelProfile

# Maps a structure_hint stage keyword to the CanonicalStory field it
# draws from. Each channel's stage keywords map one-to-one onto
# distinct CanonicalStory fields — no field is used twice within one
# channel's draft. The one keyword shared across both channels
# ("outcome") maps consistently to the same field in both.
_STAGE_TO_FIELD = {
    "problem": "core_problem",
    "context": "core_problem",
    "technical_solution": "change",
    "code/architecture": "insight",
    "personal_insight": "insight",
    "outcome": "outcome",
    "lesson": "forward_lesson",
}

# Per-channel heading label for each stage keyword, in that channel's
# own language — this is the one place actual language differences
# are hardcoded, since no runtime translation call exists in this
# prototype.
_STAGE_HEADINGS = {
    "habr": {
        "problem": "Проблема",
        "technical_solution": "Техническое решение",
        "code/architecture": "Код / архитектура",
        "outcome": "Итог",
    },
    "linkedin": {
        "context": "Context",
        "personal_insight": "Personal insight",
        "outcome": "Outcome",
        "lesson": "Lesson",
    },
}

_TITLE = {
    "habr": "Как Collector (O1) считает, что реально произошло за неделю",
    "linkedin": "What actually happened this week — measured, not assumed",
}

_EVIDENCE_LABEL = {
    "habr": "Данные",
    "linkedin": "Data",
}

_NO_EVIDENCE_NOTE = {
    "habr": (
        "Файловых evidence-записей для этого репозитория в данном "
        "снимке манифеста нет — ниже только агрегированные факты."
    ),
    "linkedin": (
        "No file-level evidence records exist for this repo in this "
        "manifest snapshot — aggregate facts only, below."
    ),
}


def _parse_stages(structure_hint: str) -> list[str]:
    return [s.strip() for s in structure_hint.split("->")]


def write_draft(story: CanonicalStory, profile: ChannelProfile) -> str:
    stages = _parse_stages(profile.structure_hint)
    headings = _STAGE_HEADINGS[profile.channel]

    lines: list[str] = [f"# {_TITLE[profile.channel]}", ""]

    for stage in stages:
        field_name = _STAGE_TO_FIELD.get(stage)
        heading = headings.get(stage, stage)
        lines.append(f"## {heading}")
        lines.append("")
        if field_name is not None:
            content = getattr(story, field_name)
            lines.append(content)
        else:
            lines.append(f"[no content mapped for stage '{stage}']")
        lines.append("")

    if profile.evidence_density == "high":
        lines.append(f"## {_EVIDENCE_LABEL[profile.channel]}")
        lines.append("")
        if story.evidence_refs:
            for i in story.evidence_refs:
                lines.append(f"- evidence[{i}]")
        else:
            lines.append(_NO_EVIDENCE_NOTE[profile.channel])
        lines.append("")

    return "\n".join(lines)
