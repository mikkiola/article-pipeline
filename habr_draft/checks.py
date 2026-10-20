"""The four mandatory checks (SPEC.md M9 requirement 44): L1, (a), (b), Q.

Pure functions over a draft and already-obtained judge output; the paid model
calls themselves are made elsewhere (run_habr_draft.py, loop.py) through llm.HabrLLM.

A check result separates three states that must never be conflated
(requirement 47): it ran and passed, it ran and failed (a content finding),
or it could not run (`executed == False`: either a technical `error`, or a
required configuration value that is unset, listed in `missing_config`).
"""

from __future__ import annotations

import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "author"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "strategy_layer"))

from habr_draft.config import ARules  # noqa: E402

UNSUPPORTED = "UNSUPPORTED"


@dataclass
class CheckResult:
    name: str
    executed: bool
    passed: bool | None
    findings: list[dict] = field(default_factory=list)
    measurements: dict = field(default_factory=dict)
    missing_config: list[str] = field(default_factory=list)
    error: str | None = None
    score: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- markdown


_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[А-ЯЁA-Z«\"(\d])")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


@dataclass
class Block:
    kind: str  # "code" | "prose" | "other"
    text: str
    lines: int = 0
    in_spoiler: bool = False


def parse_blocks(body: str, spoiler_markup: list[str] | None = None) -> list[Block]:
    blocks: list[Block] = []
    open_marker = spoiler_markup[0] if spoiler_markup and len(spoiler_markup) == 2 else None
    close_marker = spoiler_markup[1] if spoiler_markup and len(spoiler_markup) == 2 else None
    depth = 0
    para: list[str] = []
    code: list[str] = []
    fence: str | None = None
    code_depth = 0

    def flush_para() -> None:
        if not para:
            return
        text = "\n".join(para)
        first = para[0].lstrip()
        if (first.startswith("#") or first.startswith(">") or first.startswith("|")
                or first.startswith("<") or _LIST_RE.match(para[0])):
            blocks.append(Block("other", text, in_spoiler=depth > 0))
        else:
            blocks.append(Block("prose", text, in_spoiler=depth > 0))
        para.clear()

    for line in body.splitlines():
        if fence is None:
            m = _FENCE_RE.match(line)
            if m:
                flush_para()
                fence = m.group(1)
                code = []
                code_depth = depth
                continue
            if open_marker and open_marker in line:
                depth += line.count(open_marker)
            if close_marker and close_marker in line:
                depth = max(0, depth - line.count(close_marker))
            if not line.strip():
                flush_para()
            else:
                para.append(line)
        else:
            if line.strip().startswith(fence):
                blocks.append(Block("code", "\n".join(code), lines=len(code), in_spoiler=code_depth > 0))
                fence = None
            else:
                code.append(line)
    if fence is not None:  # unterminated fence: treat what was collected as code
        blocks.append(Block("code", "\n".join(code), lines=len(code), in_spoiler=code_depth > 0))
    flush_para()
    return blocks


def count_sentences(paragraph: str) -> int:
    flat = " ".join(paragraph.split())
    if not flat:
        return 0
    return len(_SENTENCE_SPLIT_RE.split(flat))


def prose_text(body: str) -> str:
    """Prose only: fenced code is removed (long code would otherwise distort
    the Cyrillic ratio of the language check)."""
    return "\n\n".join(b.text for b in parse_blocks(body) if b.kind != "code")


# ---------------------------------------------------------------------- (a)


def check_habr_rules(body: str, rules: ARules) -> CheckResult:
    """Habr rule 3 (typography/formatting), only what is objectively
    checkable. Rule 1, rule 2's judgment parts and rule 4 are human review
    and are not attempted here."""
    blocks = parse_blocks(body, rules.spoiler_markup)
    prose = [b for b in blocks if b.kind == "prose"]
    code = [b for b in blocks if b.kind == "code"]
    findings: list[dict] = []
    missing: list[str] = []

    for index, block in enumerate(prose):
        sentences = count_sentences(block.text)
        if sentences <= 2:
            findings.append(
                {"rule": "habr_rule_3_short_paragraph", "paragraph": index, "sentences": sentences}
            )

    longest = max((len(b.text) for b in prose), default=0)
    if rules.max_paragraph_chars is None:
        missing.append("a_rules.max_paragraph_chars")
    elif longest > rules.max_paragraph_chars:
        findings.append(
            {"rule": "habr_rule_3_wall_of_text", "chars": longest, "limit": rules.max_paragraph_chars}
        )

    code_lines = [b.lines for b in code]
    if rules.max_code_block_lines is None:
        missing.append("a_rules.max_code_block_lines")
    if rules.spoiler_markup is None:
        missing.append("a_rules.spoiler_markup")
    if rules.max_code_block_lines is not None and rules.spoiler_markup is not None:
        for index, block in enumerate(code):
            if block.lines > rules.max_code_block_lines and not block.in_spoiler:
                findings.append(
                    {"rule": "habr_rule_3_long_code_not_in_spoiler", "block": index,
                     "lines": block.lines, "limit": rules.max_code_block_lines}
                )

    images = len(_IMAGE_RE.findall(body))
    if images:
        findings.append({"rule": "habr_rule_3_image_size_unverifiable", "images": images})

    measurements = {
        "prose_paragraphs": len(prose),
        "longest_paragraph_chars": longest,
        "code_block_lines": code_lines,
        "images": images,
    }
    if missing:
        return CheckResult("habr_rules", False, None, findings, measurements, missing_config=missing)
    return CheckResult("habr_rules", True, not findings, findings, measurements)


# ---------------------------------------------------------------------- (b)


def _normalize_code(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def check_project_requirements(body: str, fragments: list[dict]) -> CheckResult:
    """Project acceptance requirements: Russian output and at least one code
    block that is a verbatim excerpt of a fetched fragment."""
    import language_check

    findings: list[dict] = []
    prose = prose_text(body)
    russian = language_check.looks_russian(prose)
    if not russian:
        findings.append({"rule": "output_not_russian"})

    normalized_fragments = [_normalize_code(f["content"]) for f in fragments]
    code_blocks = [_normalize_code(b.text) for b in parse_blocks(body) if b.kind == "code"]
    matched = [
        block for block in code_blocks
        if block and any(block in fragment for fragment in normalized_fragments)
    ]
    if not matched:
        findings.append({"rule": "no_verbatim_fragment"})
    unmatched = len([b for b in code_blocks if b]) - len(matched)
    if unmatched:
        findings.append({"rule": "code_block_not_in_fetched_fragments", "blocks": unmatched})

    return CheckResult(
        "project_requirements", True, not findings, findings,
        {"russian": russian, "code_blocks": len(code_blocks), "verbatim_blocks": len(matched)},
    )


# ---------------------------------------------------------------------- L1


def evaluate_l1(response: dict, brief: dict, allowed_ids: set[str], judge: dict) -> CheckResult:
    """L1 - fact verification. Deterministic part: the draft's cited ids are
    ids of the selected cluster (the existing verify_cited_facts, exact match).
    Judge part: every statement the judge listed carries at least one supplied
    id and none is UNSUPPORTED.

    WHAT THIS PROVES: the cited ids exist in what the run supplied, and the
    judge mapped each statement to supplied ids. WHAT IT DOES NOT PROVE: that
    the judge's mapping is correct - it is model-asserted."""
    import daily_linkedin_author

    findings: list[dict] = []
    try:
        daily_linkedin_author.verify_cited_facts(response, brief)
    except daily_linkedin_author.AuthorLLMError as error:
        findings.append({"rule": "cited_facts_not_in_cluster", "detail": str(error)[:300]})
    except (KeyError, TypeError):
        findings.append({"rule": "cited_facts_malformed"})

    statements = judge.get("statements")
    if not isinstance(statements, list) or not statements:
        return CheckResult(
            "l1_fact_verification", False, None, findings,
            error="judge returned no statements list",
        )
    for index, statement in enumerate(statements):
        ids = statement.get("evidence_ids") if isinstance(statement, dict) else None
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
            findings.append({"rule": "statement_without_evidence", "statement": index})
            continue
        if UNSUPPORTED in ids:
            findings.append({"rule": "statement_unsupported", "statement": index})
        unknown = [i for i in ids if i != UNSUPPORTED and i not in allowed_ids]
        if unknown:
            findings.append({"rule": "statement_cites_unknown_id", "statement": index, "ids": unknown})
    return CheckResult(
        "l1_fact_verification", True, not findings, findings,
        {"statements": len(statements)},
    )


# ----------------------------------------------------------------------- Q


def evaluate_q(judge: dict, threshold: float | None) -> CheckResult:
    score = judge.get("score")
    findings = judge.get("findings")
    if type(score) is not int or not 0 <= score <= 100 or not isinstance(findings, list):
        return CheckResult("q_infostyle", False, None, error="judge response malformed")
    clean = [f for f in findings if isinstance(f, dict)]
    if threshold is None:
        return CheckResult(
            "q_infostyle", False, None, clean, {"threshold_state": "unset"},
            missing_config=["q_threshold"], score=float(score),
        )
    return CheckResult(
        "q_infostyle", True, float(score) >= threshold, clean,
        {"threshold_state": "set", "threshold": threshold}, score=float(score),
    )
