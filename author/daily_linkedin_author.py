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

Input contract: a `DailyBrief`-SHAPED JSON object — as of 2026-09-15
(M4, ADR-0045), no longer read directly from Collector's own
`daily_brief_<date>.json`. This file's CLI now expects a path to a
JSON already in this shape, produced by
`author/linkedin_verdict_reader.py` from a completed Strategy Layer
run's `AuthoringContext` list (`author/authoring_context.py`) — the
old direct read bypassed Strategy Layer's classification/gate/framing
entirely, which is exactly the leaky abstraction this migration exists
to close. This file still knows nothing about how `mode` was decided —
it trusts `mode` as an already-decided fact and only interprets it
into a prompt branch; `build_prompt()` and everything downstream of it
are unchanged by this shift, since they only ever depended on the
dict's shape, never its origin.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

import identity_state as identity_state_module

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

# Verbatim implementation of docs/adr/0044-linkedin-daily-post-voice-
# contract.md's Decision block. Any future change to the contract
# itself is a new, superseding ADR (Immutable Lineage) — this constant
# should then be updated to match, not diverge from it.
VOICE_CONTRACT = """\
Voice contract (ADR-0044), apply these strictly and do not deviate:
- Structure: Narrative Bridge 30/40/30 + hook + CTA + evidence links.
- Length: 150-250 words, max 3 sentences/paragraph.
- Voice: first person, active voice, concrete images, no hashtags,
  0-1 emoji (self-deprecating only).
- Forbidden in the observation and the mechanism description — state
  both as plain fact, not a guess: metadiscourse openers, empty
  abstractions (approach/framework/level/process/strategy), AI clichés
  (delve/tapestry/revolutionize/game-changer/low-hanging fruit/etc),
  nominalizations, hedge words ("I suspect", "I think", "perhaps", and
  equivalents).
- Hedging scope: hedge words like "I suspect"/"I think" are reserved
  for the final commercial/speculative conclusion only — never used to
  soften the observation or the mechanism description above it.
- Causal chain rule: numbers must come from DailyBrief, never
  invented, and never state a conclusion directly without showing the
  steps that produced it. Diffstat and raw lines-changed counts may
  appear only as brief factual color, never as the evidence doing the
  persuasive work — commit counts, file counts, or a genuinely
  inferable time saved are the reader-meaningful quantities to reach
  for instead; if no real quantity fits naturally, the chain can stay
  qualitative (the steps, without an invented number).
- CTA: one open question, in-body, no direct pitch.
- Evidence: L1 internal (always, from DailyBrief), L2 public link
  (only if repo is public per live `gh repo view` check, silently
  omitted if private/check fails — no apology line), L3 market signal
  (emerges from reaction, never fabricated)."""


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY_DAILY_AUTHOR")
    if not key:
        raise AuthorLLMError(
            "ANTHROPIC_API_KEY_DAILY_AUTHOR not set in environment. Export it "
            "before running (e.g. via Bitwarden locally, or a CI secret "
            "variable in production)."
        )
    return key


def _check_repo_visibility(repo_name: str) -> bool:
    """L2 evidence tier (ADR-0044): a repo's link is only ever offered
    to the model when a live check confirms it's public. Every failure
    mode — `gh` missing, an auth error, a non-zero exit, a timeout, an
    unparseable response — is treated as not-public, logged as a
    warning, and never raised: a visibility-check failure must not
    block post generation."""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", f"mikkiola/{repo_name}", "--json", "visibility"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print(
                f"WARNING: gh repo view exited {result.returncode} for "
                f"{repo_name!r}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        return json.loads(result.stdout).get("visibility") == "PUBLIC"
    except Exception as e:
        print(f"WARNING: gh repo view failed for {repo_name!r}: {e}", file=sys.stderr)
        return False


def _build_evidence_links(per_repo: list) -> list:
    """L2 evidence tier (ADR-0044): a public GitHub link per repo,
    included only for repos a live `_check_repo_visibility` call
    confirms are public today. Computed once so both prompt builders
    share identical link-gating logic."""
    links = []
    for repo in per_repo:
        name = repo["name"]
        if _check_repo_visibility(name):
            links.append({"name": name, "url": f"https://github.com/mikkiola/{name}"})
    return links


def _evidence_links_block(links: list) -> str:
    """Renders the L2 evidence tier's prompt text. Deliberately never
    names or references an omitted repo — ADR-0044 requires silent
    omission, with no apology line anywhere, including in the
    generated post."""
    if links:
        return (
            "L2 evidence — public repo links confirmed available today "
            "(only these; never invent or guess a link for any other "
            "repo):\n" + json.dumps(links, ensure_ascii=False)
        )
    return (
        "L2 evidence — no public repo links are confirmed available "
        "today. Do not mention this in the post; write it exactly as "
        "if this evidence tier were never part of the instructions."
    )


# Fact-mode data is offered to the model as deterministic per-repository
# clusters of ID-tagged facts (Experiment 1, 2026-09-26): one cluster per
# repository with commit_count > 0, and no flat cross-repo list. Repo-based
# clustering only: no semantic/topic grouping of any kind.
FACT_KIND_SUBJECT = "commit subject"
FACT_KIND_COMMIT_COUNT = "commit count"
FACT_KIND_FILES_COUNT = "files touched count"


def build_clusters(daily_brief: dict) -> list:
    """One cluster per repository that had at least one commit, each with
    stable fact IDs `{repo}:fact_{NN}` (zero-padded, 1-indexed).

    One fact per commit subject (that repository's own messages, in the
    order given, exactly as they appear in the data), then one fact for
    the repository's commit count, then one for its files-touched count
    (computed here, not by the model). No diffstat fact: the prompt
    already forbids using lines-changed figures as evidence. A repository
    with commit_count == 0 forms no cluster and is never offered.

    Raises AuthorLLMError, rather than degrading to count-only clusters,
    when a repository's entry has no `commit_messages` key (a DailyBrief
    shape from before per-repo attribution) or when no cluster exists."""
    clusters = []
    for repo in daily_brief["per_repo"]:
        if repo["commit_count"] <= 0:
            continue
        name = repo["name"]
        if "commit_messages" not in repo:
            raise AuthorLLMError(
                f"per_repo entry for {name!r} has no 'commit_messages' key — the "
                f"DailyBrief-shaped input predates per-repo message attribution, so "
                f"per-repo fact clusters cannot be built from it."
            )
        raw_facts = [(FACT_KIND_SUBJECT, subject) for subject in repo["commit_messages"]]
        raw_facts.append((FACT_KIND_COMMIT_COUNT, str(repo["commit_count"])))
        raw_facts.append((FACT_KIND_FILES_COUNT, str(len(repo["files_touched"]))))
        facts = [
            {"id": f"{name}:fact_{index:02d}", "kind": kind, "text": text}
            for index, (kind, text) in enumerate(raw_facts, start=1)
        ]
        clusters.append({"repo": name, "facts": facts})
    if not clusters:
        raise AuthorLLMError(
            "No candidate cluster can be offered: no repository in per_repo has "
            "commit_count > 0."
        )
    return clusters


def _clusters_block(clusters: list) -> str:
    blocks = []
    for cluster in clusters:
        lines = [f"Cluster: {cluster['repo']}"]
        for fact in cluster["facts"]:
            text = (
                json.dumps(fact["text"], ensure_ascii=False)
                if fact["kind"] == FACT_KIND_SUBJECT
                else fact["text"]
            )
            lines.append(f"- {fact['id']} ({fact['kind']}): {text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


_IDENTITY_STATE_LIST_KEYS = (
    "core_positions", "emerging_positions", "recently_used",
    "underdeveloped", "open_threads",
)


def _identity_context_block(identity_state: dict, recent_posts: list) -> str:
    """Renders `identity_state` + real recent post text as generation
    context (ADR-0059 Decision point 6) — input only, never something
    the model is asked to update or restate. Returns an explicit "none
    yet" line instead of an empty section on a first run, so the prompt
    never silently omits this contract element."""
    has_state = any(identity_state.get(key) for key in _IDENTITY_STATE_LIST_KEYS) or identity_state.get(
        "trajectory"
    )
    if not has_state and not recent_posts:
        return (
            "Author identity state: none recorded yet — this is the first "
            "fact-mode post under this contract. Do not invent a prior "
            "trajectory or prior positions; treat today's position as newly "
            "forming, not a continuation of anything."
        )
    lines = [
        "Author identity state (context only — do not restate this section "
        "in the post, and do not treat it as something to update yourself; "
        "it exists only to keep today's PERSONAL POSITION consistent with "
        "the author's actual trajectory, not repetitive of an already-"
        "established position):"
    ]
    for key in _IDENTITY_STATE_LIST_KEYS:
        values = identity_state.get(key) or []
        lines.append(f"- {key}: {', '.join(values) if values else '(none yet)'}")
    lines.append(f"- trajectory: {identity_state.get('trajectory') or '(none yet)'}")
    if recent_posts:
        lines.append("")
        lines.append("Author's real recent published posts (most recent last):")
        for index, post in enumerate(recent_posts, start=1):
            lines.append(f"{index}. {post}")
    return "\n".join(lines)


# Five-step evidence-grounded reasoning structure (ADR-0059, 2026-09-29),
# replacing the facts-only structure ADR-0057 required (2026-09-24).
# Preserved unchanged from ADR-0057 (ADR-0059 Decision point 2): a post must
# never state, imply, or invent a fact about the real product, the author's
# actual historical motivation, or the external world beyond what the
# supplied fact cluster contains, and co-occurrence of two commits is never
# evidence of a causal or design relationship between them. Lifted from
# ADR-0057 (Decision point 3): the blanket prohibition on any reasoning over
# facts — reasoning is now required, provided it is framed as interpretation,
# thought experiment, or preference, never as established fact. Wording for
# the five steps and the FINAL EVIDENCE CHECK is sourced from the owner's
# standalone trial process (article-pipeline-trial-archive-20260929.tar.gz:
# trial_emergent_post.py's v4 lens-based prompt for the five steps,
# trial_identity_post.py's v2 SIXTH step for the evidence check), with the
# trial's lens-splitting (a validation technique for proving the fact
# cluster yields distinct tensions, not part of ADR-0059's shipped contract)
# omitted: this function makes one reasoning pass, not three. INVERSION is
# not restored (ADR-0059 Decision point 5). Deliberately does not embed
# STYLE_CONSTRAINTS/VOICE_CONTRACT, which still carry the Narrative Bridge
# wording and remain in use by _build_idea_fallback_prompt.
#
# Identity continuity (ADR-0059 Decision point 6, wired 2026-09-30):
# `identity_state`/`recent_posts` default to a fresh load from
# identity_state.py's persisted state when the caller doesn't supply
# them (e.g. daily_publish.py's main() passes them explicitly; a direct
# test call can omit them and still get a real, if empty-on-first-run,
# state). This function only reads them as prompt context — it never
# decides what the next identity_state should contain; see
# identity_state.py's own module docstring for why that update is
# deliberately not performed here.
def _build_fact_prompt(
    daily_brief: dict,
    identity_state: dict | None = None,
    recent_posts: list | None = None,
) -> str:
    clusters = build_clusters(daily_brief)
    # L2 links only for repositories that form a cluster: a repository
    # with no commits is not offered to the model at all.
    evidence_links = _build_evidence_links([{"name": c["repo"]} for c in clusters])
    if identity_state is None:
        identity_state = identity_state_module.load_identity_state()
    if recent_posts is None:
        recent_posts = identity_state_module.load_recent_posts()
    return f"""\
You are drafting one LinkedIn post from a single day's real engineering
activity. Work through five reasoning steps in order, then synthesize a
post from them.

Today's real data (DailyBrief), this is your ONLY source of facts —
never invent a fact, user, reason, pain point, metric, or product state
not present here. The data is grouped into candidate clusters, one per
repository that had commits today. Every fact has an ID:

{_clusters_block(clusters)}

{_identity_context_block(identity_state, recent_posts)}

What the data does and does not contain:
- Each fact is a commit subject line or a count computed from that
  repository's own data; a fact's ID refers to exactly that data point.
- The data has no commit bodies, no reasons, no test results, and no
  commit hashes. If it does not contain a reason for a change, do not
  invent one — not even in the PERSONAL POSITION step below.
- Only use information present in the supplied data above.

Selecting a cluster:
- Select exactly ONE cluster: select one repository whose cluster
  contains enough related facts to form a coherent post. If more than
  one cluster qualifies, any one of them is acceptable.
- Every step below, and the final post, uses only facts from the
  selected cluster. Do not mention facts, changes, or repositories from
  any other cluster.
- You may connect 2-3 of the selected cluster's facts into one
  connected paragraph in the FACT step instead of listing them as
  separate sentences. Connecting facts does not permit stating why
  something was done, what it leads to, or what it means — the FACT
  step's own no-interpretation rule below still applies.

Work through these five steps, in this order:

1. FACT — restate, in your own words, what the selected cluster's
   commits actually changed. Only what is directly supported by its
   facts. No interpretation, no reason, no consequence. Do not name ADR
   numbers, even if a commit subject contains one — describe the change
   in plain words instead.

2. TENSION — identify a concrete, specific gap, mismatch, asymmetry, or
   unresolved design question visible in the selected cluster itself.
   State the observation itself, not an inferred reason for it. Do not
   infer that one commit was designed to detect, cause, enable, or
   respond to another commit unless that relationship is directly
   stated in the facts. Temporal proximity or co-occurrence in the same
   batch is not evidence of a causal or design relationship — state
   only that both things are true at once, never that one explains or
   was built for the other.

3. DESIGN INSIGHT — what does this tension reveal about the kind of
   system the author wants to build, or the kind of engineering the
   author values? State this as your own interpretation, not something
   today's commits prove as a universal law. The insight must preserve
   the exact object of the tension — do not introduce a new actor,
   system capability, failure mode, causal mechanism, or market
   behavior absent from the facts, and do not depend on an unstated
   design intent. Specificity test: if this sentence could be published
   about almost any project with a similarly-shaped commit, it fails
   and must be rewritten, not hedged.

4. PERSONAL POSITION — given this tension, formulate a present-tense
   engineering preference or design value the author could reasonably
   carry forward into other systems — explicitly framed as something
   today's work may strengthen, clarify, or cause the author to
   formulate, never as a claim about the historical motivation behind
   the actual commits. The position must still originate from today's
   tension, but may be broader than what today's data proves — only the
   underlying FACT and TENSION must remain proven, not the position
   itself. If the author identity state above lists an existing
   position that already covers this tension, deepen or extend it
   rather than restating it; if it's genuinely new, say so as newly
   forming, not as something the author has always held.

5. RELEVANT PROBLEM — describe a real-world problem or pain this
   position or insight plausibly addresses, framed explicitly as an
   untested hypothesis, never as a confirmed fact about any market,
   product, or user.

Then write "post": a single synthesized LinkedIn post of 150-300 words
that moves through FACT, TENSION, DESIGN INSIGHT, PERSONAL POSITION, and
RELEVANT PROBLEM as a readable narrative. Do not include a separate
inversion or thought-experiment beat in the post. It must never present
the TENSION, DESIGN INSIGHT, or RELEVANT PROBLEM content as an
established, confirmed, or planned fact, and it must never state or
imply a historical reason for the actual commit(s) above. Include a
public repository link only if the L2 block below lists it for the
selected repository. Do not name ADR numbers as evidence.

FINAL EVIDENCE CHECK — before returning your response, inspect every
factual or causal statement in the finished post. For each one, verify
it is directly supported by the selected cluster's facts. Do not state
as fact: absence of a capability or mechanism unless the facts
explicitly establish that absence; what "nobody", "the team", "the
system", or "the author" could or could not do; causal relationships
not explicitly present in the facts; conclusions about what the work
"really was" beyond the supplied evidence; or user, business, market, or
operational impact not present in the data. Interpretations and the
personal position may go beyond the facts, but must be phrased
explicitly as interpretation or preference, never as observed fact. If a
sentence cannot pass this check, rewrite it conservatively or remove it
— do not add new information while repairing it. This check does not
constrain the personal position itself: the evidence requirement applies
to claims about reality, not to the author's stated preference.

Numbers: every number in the post must appear in the selected cluster's
facts or be a direct count of items in them (use the counts given in the
facts). Never invent a number. Do not use diffstat or lines-changed
counts as evidence.

Style constraints, apply these strictly:
- 150-300 words. Maximum 3 sentences per paragraph.
- First person, active voice. No hashtags. No emoji. No greeting.
- No motivational language, no startup clichés ("game changer",
  "revolutionary", "unlock", "supercharge"), no false certainty.
- Write in English (LinkedIn audience).

{_evidence_links_block(evidence_links)}

{OUTPUT_FORMAT_INSTRUCTIONS}

The JSON object must have exactly these keys:
- "post": the final LinkedIn post text (string). This is the only
  field intended for actual publication.
- "selected_cluster": the repository name of the one cluster you
  selected, exactly as written after "Cluster:" above (string).
- "supporting_facts": the exact fact IDs of the facts your reasoning
  and post draw on, for example ["<repo>:fact_01", "<repo>:fact_03"],
  using only IDs from the selected cluster (list of strings).
- "reasoning": an object with exactly these five string fields —
  "fact", "tension", "design_insight", "personal_position",
  "relevant_problem" — holding the text you produced for each step
  above. For the owner's own review; not published verbatim."""


# NOTE: this fallback builder still uses the Narrative Bridge structure
# (via STYLE_CONSTRAINTS/VOICE_CONTRACT) and has NOT been aligned with the
# temporary facts-only change made to _build_fact_prompt on 2026-09-24.
def _build_idea_fallback_prompt(daily_brief: dict) -> str:
    products = ", ".join(IDEA_FALLBACK_PRODUCTS)
    evidence_links = _build_evidence_links(daily_brief['per_repo'])
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

Post structure — Narrative Bridge 30/40/30 + hook + CTA + evidence
links, same shape as a fact-based post (see Voice contract below for
the exact rules each part must follow):
1. Hook — one opening line that earns the read.
2. Setup (~30% of the post) — what the chosen product actually
   is/does today, stated as plain fact, described truthfully, not
   embellished, not hedged.
3. Bridge (~40% of the post) — what it could become, explicitly framed
   as an idea, not existing functionality, stated as plain fact, not
   hedged. Where a feedback loop genuinely applies to the reimagined
   idea, connect it through the loop rather than a direct jump:
   mechanism -> less manual effort -> cheaper/faster check -> more
   checks possible -> fewer bad outcomes slip through -> compounding
   effect, using real DailyBrief quantities where they fit naturally
   (never diffstat or raw lines-changed counts); if none of this
   applies to the chosen product/idea, this step doesn't force one in.
4. Close (~30% of the post) — the CTA plus any available evidence
   links.

{STYLE_CONSTRAINTS}

{VOICE_CONTRACT}

{_evidence_links_block(evidence_links)}

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


# ADR-0059 (2026-09-29) replaces the facts-only structure's fact_or_product
# field (a one-line summary for the owner's review) with "reasoning", a
# nested object carrying the five-step evidence-grounded reasoning contract
# (fact/tension/design_insight/personal_position/relevant_problem) as
# machine-readable metadata — per the owner's B-068 decision, this metadata
# stays in the structured response, never as an in-text marker in "post",
# the field actually published. selected_cluster / supporting_facts (added
# 2026-09-26, Experiment 1) are unchanged. idea_fallback keeps its own keys,
# unchanged (ADR-0044 remains normative there).
REASONING_REQUIRED_KEYS = {
    "fact", "tension", "design_insight", "personal_position", "relevant_problem",
}
FACT_REQUIRED_KEYS = {"post", "selected_cluster", "supporting_facts", "reasoning"}
IDEA_FALLBACK_REQUIRED_KEYS = {
    "post", "fact_or_product", "emergent_property", "evidence_to_collect",
}


def build_prompt(
    daily_brief: dict,
    identity_state: dict | None = None,
    recent_posts: list | None = None,
) -> str:
    mode = daily_brief["mode"]
    if mode == "fact":
        return _build_fact_prompt(daily_brief, identity_state, recent_posts)
    if mode == "idea_fallback":
        return _build_idea_fallback_prompt(daily_brief)
    raise AuthorLLMError(f"Unknown DailyBrief mode: {mode!r} — expected 'fact' or 'idea_fallback'.")


_ADR_NUMBER_RE = re.compile(r"\bADR-\d+", re.IGNORECASE)
_GREETING_RE = re.compile(r"\b(?:Hi|Hello|Hey)\b")


def check_post_content(post: str) -> None:
    """Deterministic post check (temporary facts-only structure,
    2026-09-24). Deliberately narrow: rejects only an ADR number and a
    greeting word, and nothing else — no other content-quality or
    duplicate-prevention check lives here. Raises AuthorLLMError, so a
    rejected post fails the run before anything is published."""
    if _ADR_NUMBER_RE.search(post):
        raise AuthorLLMError(
            f"Generated post names an ADR number, which the facts-only "
            f"structure forbids. Post: {post!r}"
        )
    if _GREETING_RE.search(post):
        raise AuthorLLMError(
            f"Generated post contains a greeting (Hi/Hello/Hey), which the "
            f"facts-only structure forbids. Post: {post!r}"
        )


def verify_cited_facts(response: dict, daily_brief: dict) -> None:
    """Fact mode only. Verifies, by exact string match, that the model
    cited only what it was actually offered this run: `selected_cluster`
    must be one of the cluster names built from `daily_brief`, and every
    ID in `supporting_facts` must be an ID of that selected cluster.

    WHAT THIS PROVES: the model's citations refer to facts that exist in
    the cluster it was given. WHAT IT DOES NOT PROVE: that the post's prose
    is semantically faithful to those facts, that the cited facts actually
    support what the post says, or that the post draws on all or only the
    facts listed. A post could cite real IDs and still misstate them; this
    check does not detect that. Fail closed: any mismatch raises."""
    clusters = {c["repo"]: c for c in build_clusters(daily_brief)}
    selected = response["selected_cluster"]
    if not isinstance(selected, str) or selected not in clusters:
        raise AuthorLLMError(
            f"selected_cluster {selected!r} is not one of the clusters offered this "
            f"run: {sorted(clusters)}."
        )
    supporting = response["supporting_facts"]
    if (
        not isinstance(supporting, list)
        or not supporting
        or not all(isinstance(fact_id, str) for fact_id in supporting)
    ):
        raise AuthorLLMError(
            f"supporting_facts must be a non-empty list of fact-ID strings, got: {supporting!r}"
        )
    offered_ids = {fact["id"] for fact in clusters[selected]["facts"]}
    unknown = [fact_id for fact_id in supporting if fact_id not in offered_ids]
    if unknown:
        raise AuthorLLMError(
            f"supporting_facts cites ID(s) {unknown!r} that are not in the selected "
            f"cluster {selected!r} (offered IDs: {sorted(offered_ids)})."
        )


def validate_reasoning(response: dict) -> None:
    """Fact mode only (ADR-0059). Verifies the 'reasoning' object carries
    all five required string fields — presence and type only. This does not
    judge whether the content is itself evidence-grounded: verify_cited_facts
    covers citation grounding against supporting_facts; nothing here
    re-derives semantic correctness of the reasoning text."""
    reasoning = response.get("reasoning")
    if not isinstance(reasoning, dict):
        raise AuthorLLMError(
            f"Model response's 'reasoning' field must be an object, got: {reasoning!r}"
        )
    missing = REASONING_REQUIRED_KEYS - reasoning.keys()
    if missing:
        raise AuthorLLMError(
            f"Model response's 'reasoning' object is missing required key(s): "
            f"{sorted(missing)}. Full reasoning: {reasoning!r}"
        )
    invalid = [
        key for key in REASONING_REQUIRED_KEYS
        if not isinstance(reasoning.get(key), str) or not reasoning[key].strip()
    ]
    if invalid:
        raise AuthorLLMError(
            f"Model response's 'reasoning' object has non-string or empty "
            f"value(s) for key(s): {sorted(invalid)}. Full reasoning: {reasoning!r}"
        )


def validate_structured_response(response: dict, mode: str, daily_brief: dict | None = None) -> None:
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
    check_post_content(response["post"])
    if mode == "fact":
        validate_reasoning(response)
        if daily_brief is None:
            raise AuthorLLMError(
                "fact-mode validation needs the daily_brief the prompt was built from "
                "(to know which clusters and fact IDs were offered); none was passed."
            )
        verify_cited_facts(response, daily_brief)


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


def _extract_text_block(content: list) -> str:
    """`messages.create()`'s response.content can include a
    ThinkingBlock ahead of the TextBlock when extended thinking is
    involved — the text block is not reliably content[0], so it must
    be found by its `.type`, not assumed by position."""
    for block in content:
        if getattr(block, "type", None) == "text":
            return block.text
    block_types = [getattr(block, "type", "<unknown>") for block in content]
    raise AuthorLLMError(
        f"Model response contained no text block. Block types found: {block_types!r}"
    )


def call_model(prompt: str) -> dict:
    # thinking={"type": "disabled"} is required, not optional, on
    # claude-sonnet-5: unlike earlier Sonnet models, a request with no
    # `thinking` field runs with adaptive thinking (effort: high) by
    # default (https://platform.claude.com/docs/en/models/sonnet-5/
    # whats-new-sonnet-5). max_tokens is a hard limit on combined
    # thinking + text output, so without this, the model can exhaust
    # the entire budget on its thinking block before producing any
    # text — confirmed as the actual cause of a real production
    # failure (block_types: ['thinking'], 2026-09-24 workflow run).
    client = anthropic.Anthropic(api_key=_get_api_key())
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )
    print(f"stop_reason: {response.stop_reason}")
    raw_text = _extract_text_block(response.content)
    text = _strip_markdown_fence(raw_text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AuthorLLMError(
            f"Model response was not valid JSON: {e}\nRaw response: {raw_text!r}"
        ) from e


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Author's daily LinkedIn post generator — one LLM call, branched "
            "on DailyBrief's mode. Reads a DailyBrief-SHAPED JSON file "
            "(produced by author/linkedin_verdict_reader.py from a Strategy "
            "Layer run's AuthoringContext, per ADR-0045) — no longer reads "
            "Collector's daily_brief_<date>.json directly (M4, 2026-09-15)."
        )
    )
    parser.add_argument(
        "daily_brief_path",
        help="Path to a DailyBrief-shaped JSON file (required — no default; "
        "the old fallback to Collector's raw file was the direct-read bypass "
        "this migration closes).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    daily_brief_path = Path(args.daily_brief_path)

    daily_brief = json.loads(daily_brief_path.read_text())
    prompt = build_prompt(daily_brief)
    response = call_model(prompt)
    validate_structured_response(response, daily_brief["mode"], daily_brief)

    date_token = daily_brief.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"draft_linkedin_daily_{date_token}.json"
    out_path.write_text(json.dumps(response, indent=2, ensure_ascii=False) + "\n")

    print(f"Read {daily_brief_path} (mode={daily_brief['mode']})")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
