"""Stage 3: Channel Profile — explicit profile objects, not a scalar tone.

Exactly two profiles for this pilot's two channels. No registry, no
dynamic lookup, no base class — this pilot has two channels; these are
the two channels.
"""

from dataclasses import dataclass


@dataclass
class ChannelProfile:
    channel: str
    language: str
    audience: str
    purpose: str
    evidence_density: str
    narrative_mode: str
    structure_hint: str


HABR_RU = ChannelProfile(
    channel="habr",
    language="ru",
    audience="technical_builders",
    purpose="demonstrate_engineering",
    evidence_density="high",
    narrative_mode="technical_case",
    structure_hint="problem -> technical_solution -> code/architecture -> outcome",
)

LINKEDIN_EN = ChannelProfile(
    channel="linkedin",
    language="en",
    audience="professional_peers",
    purpose="professional_journey",
    evidence_density="medium",
    narrative_mode="personal_reflection",
    structure_hint="context -> personal_insight -> outcome -> lesson",
)
