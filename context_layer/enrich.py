"""Context Layer — mechanical context enrichment (context_layer/SPEC.md, Milestone 1).

Deterministic enrichment transformation, not a standalone storage/
processing component (see SPEC.md "Архитектурная модель"): takes a
Claim record, returns the same record with an added `context` field.

Self-contained by design — does not read or modify `atom_selector.py`
or `graph_reader.py` in `claim_extraction/` (SPEC.md Goals/FR#1).
BRAIN_REPO_DIR resolution is duplicated here rather than imported,
following the same copy-not-share precedent already used for
`graph_reader.py` itself (see that file's own docstring).
"""

from __future__ import annotations

import json
import os
import re

_LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_paths.json")

TAG_PATTERN = re.compile(r"#([\w\-/]+)")
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def _resolve_brain_repo_dir() -> str:
    env_value = os.environ.get("BRAIN_REPO_DIR")
    if env_value:
        return env_value
    if os.path.exists(_LOCAL_CONFIG_PATH):
        with open(_LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)["brain_repo_dir"]
    raise RuntimeError(
        "BRAIN_REPO_DIR не настроен. Задай переменную окружения BRAIN_REPO_DIR "
        "или создай context_layer/local_paths.json ({\"brain_repo_dir\": \"...\"})."
    )


def extract_context(atom_path: str) -> dict:
    """Механически извлекает tags и wiki_links из сырого текста атома.

    `atom_path` — путь из Claim-записи, относительный BRAIN_REPO_DIR
    (например "02_Cards/Атом.md"), как записывает его atom_selector.py.
    """
    brain_repo_dir = _resolve_brain_repo_dir()
    full_path = os.path.join(brain_repo_dir, atom_path)
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    tags = TAG_PATTERN.findall(content)
    wiki_links = WIKI_LINK_PATTERN.findall(content)
    return {"tags": tags, "wiki_links": wiki_links}


def backfill_pilot_run(input_path: str) -> list[dict]:
    """Возвращает новый список Claim-записей из input_path с добавленным `context`.

    Не перезаписывает input_path — только возвращает данные; запись
    нового файла на диск (Immutable Lineage) — Milestone 2, не эта
    функция.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        claims = json.load(f)

    enriched = []
    for claim in claims:
        new_claim = dict(claim)
        new_claim["context"] = extract_context(claim["atom_path"])
        enriched.append(new_claim)
    return enriched
