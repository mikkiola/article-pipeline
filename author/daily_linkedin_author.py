#!/usr/bin/env python3
"""Author's daily LinkedIn post generator — the only LLM/API call in this
whole architecture.

Standalone, parallel to the existing v1 templating pipeline
(source_adapter.py -> story_builder.py -> channel_author.py ->
generate_drafts.py) — does not import from or modify any of those
files. This is a first version meant to prove the linear pipeline
works and produce real Evidence to inspect, not a sophisticated
system: exactly one LLM call per run, no retry, no multi-turn
conversation, no self-correction pass. Any failure — missing API key,
malformed model response — fails loudly; there is no fallback path.

Input contract: a `DailyBrief` JSON object, produced by
`collector/scripts/daily_brief.py` (a separate repo, sibling directory
under the same workspace root). This file knows nothing about how
`mode` was decided — it trusts `mode` as an already-decided fact and
only interprets it into a prompt branch.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# Model used for this component's single LLM call.
MODEL = "claude-sonnet-5"


class AuthorLLMError(RuntimeError):
    """Raised when the model call, its response, or the API key setup
    cannot be trusted to produce a usable result."""


# Fixed list of already-built products this component can pick from in
# idea_fallback mode. Selection order among them doesn't matter — owner
# confirmed. Kept as a named, easily-editable constant, not inlined
# into the prompt text.
IDEA_FALLBACK_PRODUCTS = ["Collector", "Author", "article-pipeline (as a whole)"]

STYLE_CONSTRAINTS = """\
Style constraints, apply these strictly:
- No motivational language, no startup clichés ("game changer",
  "revolutionary", "unlock", "supercharge"), no forced personal-branding
  tone, no false certainty.
- Register: "I saw this -> tried looking at it differently -> here's
  what unexpectedly comes out -> curious if there's a real pain here."
- Short, concrete, novel enough to prompt a thought or reply. Not
  promotional, not motivational.
- Write in English (LinkedIn audience).
- Keep FACT (what happened), IDEA (an interpretation/reimagining), and
  HYPOTHESIS (an untested guess) distinct in the text. Never present a
  HYPOTHESIS as an established fact. Never invent evidence, numbers,
  users, or product state that isn't in the data given to you below."""

OUTPUT_FORMAT_INSTRUCTIONS = """\
Respond with a single JSON object only — no markdown code fences, no
text before or after the JSON, no explanation outside the JSON object
itself."""


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY_DAILY_AUTHOR")
    if not key:
        raise AuthorLLMError(
            "ANTHROPIC_API_KEY_DAILY_AUTHOR not set in environment. Export it "
            "before running (e.g. via Bitwarden locally, or a CI secret "
            "variable in production)."
        )
    return key


def _build_fact_prompt(daily_brief: dict) -> str:
    return f"""\
You are drafting one LinkedIn post from a single day's real engineering
activity. Work through four internal steps before writing the post —
the post itself must surface only the strongest resulting line, not
all four operations explicitly enumerated. The reader should see the
insight, not the method.

Today's real data (DailyBrief), this is your ONLY source of facts —
never invent a fact, user, pain point, metric, or product state not
present here:
- total_diffstat: {daily_brief['total_diffstat']}
- files_touched: {json.dumps(daily_brief['files_touched'], ensure_ascii=False)}
- commit_messages: {json.dumps(daily_brief['commit_messages'], ensure_ascii=False)}
- per_repo breakdown: {json.dumps(daily_brief['per_repo'], ensure_ascii=False)}

Internal steps:
1. FACT — identify the single most substantive fact of the day, drawn
   only from the data above.
2. EMERGENT PROPERTY — look at the mechanism actually built, separate
   from its current intended product, and find what unexpected
   property appears if the object, user, scale, context, or
   decision-point changes.
3. INVERSION — invert the possibility found in step 2 (opposite goal,
   producer/consumer swap, absence instead of presence, prevent-X
   instead of help-with-X). The inversion must have a causal link back
   to the original mechanism from step 1 — not be an unrelated new idea.
4. COMMERCIAL HYPOTHESIS — one concrete potential pain: who
   specifically feels it, what they do today instead, why that's bad,
   what outcome they'd want. If there is no real basis for this in the
   data, phrase it explicitly as a hypothesis ("I suspect that...").
   Never phrase it as a market assertion ("Companies want...").

Post structure (three parts, no explicit step labels in the post text):
1. What actually happened, citing a concrete evidence reference from
   the data above (e.g. a repo name, a diffstat number, a file name) —
   never invented specifics.
2. What unexpectedly emerges, explicitly framed as an idea/possibility,
   not as existing functionality.
3. A "could someone pay for this?" close whose call-to-action asks for
   market evidence (e.g. "if you run into this, I'd be curious how
   common it actually is") — never a "hire me" / "DM me" ask.

{STYLE_CONSTRAINTS}

{OUTPUT_FORMAT_INSTRUCTIONS}

The JSON object must have exactly these keys:
- "post": the final LinkedIn post text (string). This is the only
  field intended for actual publication.
- "fact_or_product": the step-1 FACT you identified (string).
- "emergent_property": the step-2 result (string).
- "inversion": the step-3 result (string).
- "commercial_hypothesis": the step-4 result (string).

The last four fields are for the owner's own Evidence review, not for
publication — they will not be posted."""


def _build_idea_fallback_prompt(daily_brief: dict) -> str:
    products = ", ".join(IDEA_FALLBACK_PRODUCTS)
    return f"""\
Today's engineering activity was too quiet or inconclusive for a
fact-based post (see DailyBrief's own metrics below, for context only
— this branch does not require citing them in the post). Instead,
pick exactly ONE already-built product from this fixed list: {products}.

Describe that product truthfully as it exists today, then generate a
genuine "new application for an existing thing" idea: a reimagining of
what it could become for a different audience, context, or use case.
This implies zero new code — it is a reframing, not a roadmap item.

Context only, not required in the post itself:
- total_diffstat: {daily_brief['total_diffstat']}
- commit_messages: {json.dumps(daily_brief['commit_messages'], ensure_ascii=False)}

Post structure (three parts, same shape as a fact-based post):
1. What the chosen product actually is/does today — described
   truthfully, not embellished.
2. What it could become, explicitly framed as an idea, not existing
   functionality.
3. A "could someone pay for this?" close whose call-to-action asks for
   market evidence (e.g. "if you run into this, I'd be curious how
   common it actually is") — never a "hire me" / "DM me" ask.

{STYLE_CONSTRAINTS}

{OUTPUT_FORMAT_INSTRUCTIONS}

The JSON object must have exactly these keys:
- "post": the final LinkedIn post text (string). This is the only
  field intended for actual publication.
- "fact_or_product": which product from the list you chose (string).
- "emergent_property": the reimagined idea you generated (string).
- "evidence_to_collect": what real-world evidence would confirm or
  disconfirm actual demand for this reimagined idea (string).

The last two fields are for the owner's own Evidence review, not for
publication — they will not be posted."""


FACT_REQUIRED_KEYS = {
    "post", "fact_or_product", "emergent_property", "inversion", "commercial_hypothesis",
}
IDEA_FALLBACK_REQUIRED_KEYS = {
    "post", "fact_or_product", "emergent_property", "evidence_to_collect",
}


def build_prompt(daily_brief: dict) -> str:
    mode = daily_brief["mode"]
    if mode == "fact":
        return _build_fact_prompt(daily_brief)
    if mode == "idea_fallback":
        return _build_idea_fallback_prompt(daily_brief)
    raise AuthorLLMError(f"Unknown DailyBrief mode: {mode!r} — expected 'fact' or 'idea_fallback'.")


def validate_structured_response(response: dict, mode: str) -> None:
    required = FACT_REQUIRED_KEYS if mode == "fact" else IDEA_FALLBACK_REQUIRED_KEYS
    missing = required - response.keys()
    if missing:
        raise AuthorLLMError(
            f"Model response missing required key(s) for mode={mode!r}: "
            f"{sorted(missing)}. Full response: {response!r}"
        )
    if not isinstance(response.get("post"), str) or not response["post"].strip():
        raise AuthorLLMError(
            f"Model response's 'post' field must be a non-empty string, "
            f"got: {response.get('post')!r}"
        )


def _strip_markdown_fence(text: str) -> str:
    """Mechanical unwrapping only, not a retry: some models still wrap
    JSON in ```/```json fences despite being told not to."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def call_model(prompt: str) -> dict:
    client = anthropic.Anthropic(api_key=_get_api_key())
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.content[0].text
    text = _strip_markdown_fence(raw_text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AuthorLLMError(
            f"Model response was not valid JSON: {e}\nRaw response: {raw_text!r}"
        ) from e


def default_daily_brief_path() -> Path:
    """Collector is a sibling repo under the same workspace root
    (confirmed: article-pipeline/author/../.. == the workspace root
    that also contains collector/, matching tier0_scan.py's own
    WORKSPACE_ROOT layout) — not a subdirectory, not an env-configured
    path."""
    collector_data_dir = Path(__file__).resolve().parent.parent.parent / "collector" / "data"
    candidates = sorted(collector_data_dir.glob("daily_brief_*.json"))
    if not candidates:
        print(f"No daily_brief_*.json found in {collector_data_dir}", file=sys.stderr)
        sys.exit(1)
    return candidates[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Author's daily LinkedIn post generator — one LLM call, branched on DailyBrief's mode."
    )
    parser.add_argument(
        "daily_brief_path",
        nargs="?",
        help="Path to a daily_brief_<date>.json (default: latest in the sibling collector/data/ directory)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    daily_brief_path = Path(args.daily_brief_path) if args.daily_brief_path else default_daily_brief_path()

    daily_brief = json.loads(daily_brief_path.read_text())
    prompt = build_prompt(daily_brief)
    response = call_model(prompt)
    validate_structured_response(response, daily_brief["mode"])

    date_token = daily_brief.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"draft_linkedin_daily_{date_token}.json"
    out_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n")

    print(f"Read {daily_brief_path} (mode={daily_brief['mode']})")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
