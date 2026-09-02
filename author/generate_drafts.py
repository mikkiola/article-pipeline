"""Orchestrator: Source Adapter -> Story Builder -> Channel Author (x2).

Builds exactly one CanonicalEvent and one CanonicalStory, then calls
write_draft() once per channel profile against that same story object
— per this pipeline's core constraint, both channel drafts come from
one canonical story, never two independent generations from raw facts.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import source_adapter
import story_builder
import channel_author
from channel_profiles import HABR_RU, LINKEDIN_EN

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def main() -> None:
    manifest_path = source_adapter.latest_collector_manifest_path()
    manifest = json.loads(manifest_path.read_text())
    event = source_adapter.adapt_collector_manifest(manifest, repo_filter="collector")
    story = story_builder.build_story(event)

    habr_draft = channel_author.write_draft(story, HABR_RU)
    linkedin_draft = channel_author.write_draft(story, LINKEDIN_EN)

    date_token = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    habr_path = OUTPUT_DIR / f"draft_habr_{date_token}.md"
    linkedin_path = OUTPUT_DIR / f"draft_linkedin_{date_token}.md"

    habr_path.write_text(habr_draft)
    linkedin_path.write_text(linkedin_draft)

    print(f"Wrote {habr_path}")
    print(f"Wrote {linkedin_path}")


if __name__ == "__main__":
    main()
