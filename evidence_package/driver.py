"""Driver script for the Evidence Package pilot — search phase (SPEC.md, M3).

Reads Claims with status "claim" from the most recent
claim_extraction/output/pilot_run_*.json, builds one search query per
Claim, and calls search_backend.search() under a hard request budget.

Out of scope for this script (see SPEC.md):
  - Assigning status/source_url/license/note per Claim is an
    interactive Claude Code judgment call (M4), not automated here —
    except the network-error and budget-exhausted cases below, which
    SPEC.md fixes as automatic outcomes regardless of interactive
    review.
  - Writing evidence_run_*.json / evidence_log_*.json (M5, Immutable
    Lineage) — this script returns in-memory records only.

MAX_REQUESTS_PER_CLAIM is the ceiling SPEC.md allows per Claim across
both this script and any interactive retry — SPEC.md is explicit that
the second attempt only happens if the first result isn't relevant
enough, judged by the interactive M4 session, not automatically here.
This script itself only ever makes the first attempt, so on its own it
never exceeds one request per Claim.
"""

from __future__ import annotations

import glob
import json
import os
import re
from datetime import datetime, timezone

from search_backend import search as linkup_search

MAX_REQUESTS_PER_CLAIM = 2  # SPEC.md: "до 2 раз на Claim"
MAX_REQUESTS_PER_RUN = 20  # SPEC.md: "жёсткий лимит на весь прогон — 20 запросов"


class SearchBudgetError(RuntimeError):
    """Raised when a retry would exceed the per-Claim or run-wide budget."""

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CLAIM_EXTRACTION_OUTPUT_DIR = os.path.join(_THIS_DIR, "..", "claim_extraction", "output")

_PILOT_RUN_RE = re.compile(r"^pilot_run_(\d{8}T\d{6})\.json$")


def find_latest_pilot_run(output_dir: str = CLAIM_EXTRACTION_OUTPUT_DIR) -> str:
    candidates = []
    for path in glob.glob(os.path.join(output_dir, "pilot_run_*.json")):
        match = _PILOT_RUN_RE.match(os.path.basename(path))
        if match:
            candidates.append((match.group(1), path))
    if not candidates:
        raise FileNotFoundError(f"No pilot_run_*.json found in {output_dir}")
    candidates.sort(key=lambda pair: pair[0])
    return candidates[-1][1]


def load_claims(pilot_run_path: str, limit: int = 10) -> list[dict]:
    with open(pilot_run_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    return [r for r in records if r.get("status") == "claim"][:limit]


def build_search_query(claim: dict) -> str:
    """Builds the Linkup search query text for a Claim.

    Additive only (context_layer/SPEC.md FR#3/invariant): the existing
    novelty+basis text is never modified. When claim["context"] is
    present and non-empty (tags/wiki_links from context_layer), its
    terms are appended, space-joined, after the novelty+basis text.
    When "context" is absent (every Claim before context_layer's
    Milestone 2/3) or present but empty, output is byte-identical to
    the pre-context_layer behavior.
    """
    query = f"{claim['novelty']['value']} {claim['basis']['value']}"
    context = claim.get("context")
    if context:
        extra_terms = context.get("tags", []) + context.get("wiki_links", [])
        if extra_terms:
            query = f"{query} {' '.join(extra_terms)}"
    return query


# Pilot extension (flagged, not part of SPEC.md's search_query formula —
# same "flag it as an addition" treatment as D-024): hand-translated
# RU->EN search queries for this run's 5 Claims, produced interactively
# by Claude Code (D-015 — no translation API/vendor added; linkup-sdk
# and the other installed dependencies expose no translation). Chinese
# is deferred to a later iteration, not this run. Keyed by the exact
# Russian text build_search_query() produces, so a stale/missing entry
# fails loudly via KeyError instead of silently searching the wrong
# text.
QUERY_TRANSLATIONS_RU_EN: dict[str, str] = {
    'Разнообразия агентов недостаточно для генерации нового — нужны несовместимые/конфликтующие стимулы (функции вознаграждения); напряжение между агентами с разными стимулами — не сбой, а механизм генерации нового. Атом обосновывает тезис внутренней логикой и собственным иллюстративным примером (пять ролей с несовместимыми метриками вознаграждения) — пример придуман самим атомом как иллюстрация, не как внешне проверяемый случай, поэтому это не внешняя фактическая опора.': 'Diversity among agents alone is not enough to generate novelty — incompatible/conflicting incentives (reward functions) are needed; tension between agents with different incentives is not a malfunction but a mechanism for generating novelty. The atom justifies the thesis through internal logic and its own illustrative example (five roles with incompatible reward metrics) — the example is invented by the atom itself as an illustration, not as an externally verifiable case, so this is not external factual support.',
    'Расширение познавательных/технологических возможностей не сокращает пространство неизвестного, а увеличивает его быстрее, чем пространство известного — вопреки интуиции, что прогресс приближает к «завершению картины мира». Атом обосновывает инвариант конкретными историческими примерами — телескоп, квантовая механика, генетика, компьютеры — каждый из которых, по истории науки, не закрыл вопросы, а породил новые области исследования; это апелляция к внешне проверяемым историческим фактам о развитии науки, а не только к внутренней логике атома.': 'Expanding cognitive/technological capabilities does not shrink the space of the unknown but grows it faster than the space of the known — contrary to the intuition that progress brings us closer to "completing the picture of the world." The atom grounds this invariant in concrete historical examples — the telescope, quantum mechanics, genetics, computers — each of which, according to the history of science, did not close questions but spawned new fields of research; this is an appeal to externally verifiable historical facts about the development of science, not just to the atom\'s internal logic.',
    'Опасность — не в том, что данные устарели, а в отсутствии сигнала/механизма, который бы это обнаружил; «живучесть» системы определяется способностью замечать, когда знания перестают быть верными, а не тем, что она хранит верные знания. Атом обосновывает тезис исключительно внутренней логикой (знание нуждается не только в хранении, но и в механизме проверки актуальности) — без внешних данных, источников или примеров.': 'The danger is not that the data has become outdated, but the absence of a signal/mechanism that would detect this; a system\'s "resilience" is determined by its ability to notice when knowledge stops being true, not by the fact that it stores true knowledge. The atom justifies the thesis purely through internal logic (knowledge needs not only storage but also a mechanism for checking its relevance) — without external data, sources, or examples.',
    'Системы наблюдения за обществом подвержены эффекту наблюдателя — сам акт измерения (например, настроения) меняет то, что измеряется; задача сводится к минимизации этого искажения, а не к его полному устранению. Атом обосновывает тезис отсылкой к общему явлению «эффект наблюдателя» (по аналогии с одноимённым феноменом), но не приводит конкретных проверяемых данных или примеров измерения — только называет явление, не подтверждает его внешними данными в тексте.': 'Systems that observe society are subject to the observer effect — the very act of measurement (for example, of sentiment) changes what is being measured; the task reduces to minimizing this distortion, not eliminating it entirely. The atom justifies the thesis by referencing the general phenomenon of the "observer effect" (by analogy with the eponymous phenomenon), but does not provide concrete verifiable data or measurement examples — it only names the phenomenon without confirming it with external data in the text.',
    'Архитектура управляема только тогда, когда заранее определяет не только переходы/продолжение работы, но и явные условия остановки/выхода из процессов — условия остановки такая же часть архитектуры, как цели, роли и правила взаимодействия. Атом обосновывает тезис исключительно внутренней логикой (система без явных критериев завершения процессов «перестаёт принимать решения и начинает просто продолжаться») — без внешних данных, источников или примеров.': 'Architecture is manageable only when it defines in advance not only transitions/continuation of work but also explicit stopping/exit conditions for processes — stopping conditions are as much a part of architecture as goals, roles, and interaction rules. The atom justifies the thesis purely through internal logic (a system without explicit process-termination criteria "stops making decisions and just continues") — without external data, sources, or examples.',
}


def translate_query(text: str) -> str:
    """English translation of a Russian search_query (pilot extension,
    not part of SPEC.md's search_query formula). Looks up a hand-
    translated table instead of calling a translation API/vendor.
    Raises KeyError if `text` hasn't been translated yet.
    """
    return QUERY_TRANSLATIONS_RU_EN[text]


def run_searches(
    claims: list[dict],
    search_fn=linkup_search,
    max_requests_per_run: int = MAX_REQUESTS_PER_RUN,
    use_translation: bool = False,
) -> tuple[list[dict], dict]:
    """Run one search attempt per Claim under the run-wide budget.

    Returns (records, log_summary). `records` carries one dict per
    Claim with `status` left as None when a search succeeded (awaiting
    M4's interactive assessment), or preset to "unverifiable" /
    "pending" for the two automatic outcomes SPEC.md defines.

    use_translation: pilot extension (not in SPEC.md), default False —
    existing callers are unaffected. When True, search_fn() is called
    with the English translation of the query instead of the Russian
    original, and each record additionally carries `search_query_en`.
    `search_query` itself always stays the Russian original, unchanged.
    """
    records = []
    events = []
    requests_used_total = 0
    budget_exhausted = False

    for claim in claims:
        claim_id = claim["claim_id"]
        query = build_search_query(claim)
        query_en = translate_query(query) if use_translation else None
        api_query = query_en if use_translation else query

        if requests_used_total >= max_requests_per_run:
            budget_exhausted = True
            record = {
                "claim_id": claim_id,
                "search_query": query,
                "requests_used": 0,
                "search_results": None,
                "status": "pending",
                "note": None,
                "searched_at": None,
            }
            if use_translation:
                record["search_query_en"] = query_en
            records.append(record)
            continue

        searched_at = datetime.now(timezone.utc).astimezone().isoformat()
        try:
            results = search_fn(api_query)
        except Exception as exc:
            # Broad catch is deliberate here: this is the external network
            # boundary SPEC.md requires resilience against ("любая сетевая
            # ошибка/таймаут... не должна ронять весь прогон"), and the
            # linkup-sdk error classes share no common base to narrow on.
            requests_used_total += 1
            error_text = f"{type(exc).__name__}: {exc}"
            events.append({
                "type": "search_error",
                "claim_id": claim_id,
                "error": error_text,
                "at": searched_at,
            })
            record = {
                "claim_id": claim_id,
                "search_query": query,
                "requests_used": 1,
                "search_results": None,
                "status": "unverifiable",
                "note": f"Сетевая ошибка/таймаут Linkup: {error_text}",
                "searched_at": searched_at,
            }
            if use_translation:
                record["search_query_en"] = query_en
            records.append(record)
            continue

        requests_used_total += 1
        record = {
            "claim_id": claim_id,
            "search_query": query,
            "requests_used": 1,
            "search_results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
            ],
            "status": None,
            "note": None,
            "searched_at": searched_at,
        }
        if use_translation:
            record["search_query_en"] = query_en
        records.append(record)

    if budget_exhausted:
        events.append({"type": "budget_exhausted", "requests_used_total": requests_used_total})

    log_summary = {
        "requests_used_total": requests_used_total,
        "search_budget_exhausted": budget_exhausted,
        "events": events,
    }
    return records, log_summary


def retry_search(
    record: dict,
    requests_used_total: int,
    search_fn=linkup_search,
    max_requests_per_claim: int = MAX_REQUESTS_PER_CLAIM,
    max_requests_per_run: int = MAX_REQUESTS_PER_RUN,
) -> dict:
    """Make a second search attempt for one Claim (interactive M4 call only).

    Enforces both budgets as hard checks, not just the declared
    constants: raises SearchBudgetError instead of silently exceeding
    either cap. Mutates and returns `record` — appends the new results,
    bumps `requests_used`, updates `searched_at`. Does not touch
    run-wide bookkeeping beyond validating against the caller-supplied
    `requests_used_total`; the caller (M4 session) is responsible for
    tracking that total across all Claims in the run.
    """
    if record["requests_used"] >= max_requests_per_claim:
        raise SearchBudgetError(
            f"{record['claim_id']}: per-Claim budget exhausted "
            f"({record['requests_used']}/{max_requests_per_claim})"
        )
    if requests_used_total >= max_requests_per_run:
        raise SearchBudgetError(
            f"{record['claim_id']}: run-wide budget exhausted "
            f"({requests_used_total}/{max_requests_per_run})"
        )

    results = search_fn(record["search_query"])
    record["requests_used"] += 1
    record["search_results"] = (record["search_results"] or []) + [
        {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
    ]
    record["searched_at"] = datetime.now(timezone.utc).astimezone().isoformat()
    return record


def main() -> None:
    pilot_run_path = find_latest_pilot_run()
    claims = load_claims(pilot_run_path)
    print(f"pilot_run source: {pilot_run_path}")
    print(f"claims loaded: {len(claims)}")
    records, log_summary = run_searches(claims)
    for record in records:
        result_count = len(record["search_results"]) if record["search_results"] else 0
        print(
            f"{record['claim_id']}: requests_used={record['requests_used']} "
            f"status={record['status']} results={result_count}"
        )
    print(
        f"requests_used_total={log_summary['requests_used_total']} "
        f"search_budget_exhausted={log_summary['search_budget_exhausted']}"
    )


if __name__ == "__main__":
    main()
