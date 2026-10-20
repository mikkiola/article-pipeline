"""Shared fixtures for the Habr draft tests. No test makes a network call or
a paid model call: the model caller and the GitHub getter are always injected.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("", "strategy_layer", "strategy_layer/adapters", "author"):
    sys.path.insert(0, str(ROOT / sub) if sub else str(ROOT))

import pytest  # noqa: E402

from habr_draft import prompts  # noqa: E402
from habr_draft.config import ARules, AllowListEntry, Budget, HabrConfig  # noqa: E402
from habr_draft.fragments import FetchResult  # noqa: E402

FRAGMENT_CONTENT = "@@ -1,2 +1,3 @@\n def build():\n+    return compute(x)\n     pass"

GOOD_BODY = (
    "# Как мы добавили вычисление\n\n"
    "Мы изменили функцию сборки в репозитории. Раньше она возвращала пустое значение. "
    "Теперь она вызывает вычисление и возвращает результат.\n\n"
    "Ниже приведён сам фрагмент изменения из коммита. Он показывает, что именно поменялось в функции. Остальной код файла остался без правок.\n\n"
    "```diff\n@@ -1,2 +1,3 @@\n def build():\n+    return compute(x)\n     pass\n```\n\n"
    "Изменение затрагивает одну функцию. Тест на сборку остался прежним. "
    "Других файлов коммит не трогает.\n"
)


def make_config(**overrides) -> HabrConfig:
    base = dict(
        paid_calls_enabled=True,
        model="claude-sonnet-5-5",
        api_key_env="ANTHROPIC_API_KEY_HABR_DRAFT",
        q_threshold=70.0,
        a_rules=ARules(max_paragraph_chars=2000, max_code_block_lines=20,
                       spoiler_markup=["<spoiler>", "</spoiler>"]),
        budget=Budget(max_run_spend_usd=100.0, max_fragment_chars_per_attempt=10000,
                      max_tokens_generation=1000, max_tokens_judge=500,
                      price_in_per_mtok=2.0, price_out_per_mtok=10.0),
        allow_list=[AllowListEntry(repo=r, branch="main", content_safety_checked=True,
                                   authorship_checked=True)
                    for r in ("article-pipeline", "radar", "tooltempest")],
        owner_identities=[{"login": "mikkiola"}],
        owner_authorization={"date": "2026-10-15"},
        calibration_approval={"date": "2026-10-15", "budget_usd": 1.0},
    )
    base.update(overrides)
    return HabrConfig(**base)


def good_fragment(repo="article-pipeline"):
    import hashlib
    return {"id": f"{repo}:frag_01", "repo": repo, "sha": "a" * 40, "path": "src/build.py",
            "content": FRAGMENT_CONTENT,
            "content_sha256": hashlib.sha256(FRAGMENT_CONTENT.encode()).hexdigest()}


def selection_ok(repo="article-pipeline"):
    return {
        "status": "ok", "date": "2026-10-15", "daily_brief_sha256": "d" * 64,
        "gate": {"status": "open"}, "excluded": [],
        "units": [{"repo": repo, "branch": "main", "head_sha": "b" * 40, "commit_count": 1,
                   "files_touched": ["src/build.py"],
                   "commit_messages": [{"sha": "a" * 40, "subject": "feat: compute in build",
                                        "why": None, "effect": None}]}],
    }


def write_selection(tmp_path, selection):
    path = tmp_path / "selection_input.json"
    path.write_text(json.dumps(selection), encoding="utf-8")
    return path


def fetch_ok(unit):
    return FetchResult(fragments=[good_fragment(unit["repo"])])


def purpose_of(system):
    return {
        prompts.GENERATION_SYSTEM: "generation",
        prompts.REVISION_SYSTEM: "revision",
        prompts.L1_SYSTEM: "l1",
        prompts.Q_SYSTEM: "q",
        prompts.REFERENCE_Q_SYSTEM: "reference",
    }[system]


class ScriptedCaller:
    """Stands in for call_model. `plan` maps a purpose to a list of
    responses (dicts) or exceptions to raise, consumed in order; the last
    entry repeats. Records every call."""

    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    def __call__(self, prompt, *, model, max_tokens, api_key_env, system=None, usage_sink=None):
        purpose = purpose_of(system)
        self.calls.append({"purpose": purpose, "prompt": prompt, "system": system,
                           "model": model, "max_tokens": max_tokens, "api_key_env": api_key_env})
        queue = self.plan[purpose]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, BaseException):
            raise item
        if usage_sink is not None:
            usage_sink["input_tokens"] = 100
            usage_sink["output_tokens"] = 50
        return item


def good_plan():
    return {
        "generation": [{"title": "Заголовок", "body_markdown": GOOD_BODY,
                        "selected_cluster": "article-pipeline",
                        "supporting_facts": ["article-pipeline:fact_01"]}],
        "revision": [{"title": "Заголовок", "body_markdown": GOOD_BODY,
                      "selected_cluster": "article-pipeline",
                      "supporting_facts": ["article-pipeline:fact_01"]}],
        "l1": [{"statements": [{"text": "функция вызывает вычисление",
                                "evidence_ids": ["article-pipeline:fact_01", "article-pipeline:frag_01"]}]}],
        "q": [{"score": 90, "findings": []}],
        "reference": [{"score": 80, "findings": [{"criterion": "ai_markers", "severity": "minor"}]}],
    }
