"""
Graph Reader — общая утилита чтения графа атомов (02_Cards/).

CARDS_DIR и detect_cluster() вынесены из agent.py, чтобы Article Pipeline
(atom_selector.py) не зависел от Drift (agent.py) напрямую.

Копия из brain.git (repo: локальный чекаут brain.git, путь машинно-зависим —
см. BRAIN_REPO_DIR ниже), коммит e7fbc45 ("refactor: extract
detect_cluster/CARDS_DIR to graph_reader.py"). Скопирована для пилота Claim
Extraction (SPEC.md, Article Pipeline) — может разойтись с оригиналом,
синхронизировать вручную при изменениях в brain.git.

Единственное отличие от оригинала: CARDS_DIR указывает на 02_Cards/ в brain.git
абсолютным путём, а не относительно расположения этого файла — в оригинале
02_Cards/ лежит рядом с graph_reader.py, здесь (claim_extraction/) это не так.

BRAIN_REPO_DIR — машинно-зависимый путь, не хардкодится в коде (репозиторий
уходит в публичный доступ, путь содержит локальное имя пользователя/хендл).
Настройка (нужна один раз на чекаут):
  - переменная окружения BRAIN_REPO_DIR, ИЛИ
  - claim_extraction/local_paths.json (в .gitignore, не коммитится):
    {"brain_repo_dir": "/абсолютный/путь/к/твоему/чекауту/brain"}
"""

import os
import json

_LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_paths.json")


def _resolve_brain_repo_dir() -> str:
    env_value = os.environ.get("BRAIN_REPO_DIR")
    if env_value:
        return env_value
    if os.path.exists(_LOCAL_CONFIG_PATH):
        with open(_LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)["brain_repo_dir"]
    raise RuntimeError(
        "BRAIN_REPO_DIR не настроен. Задай переменную окружения BRAIN_REPO_DIR "
        "или создай claim_extraction/local_paths.json (см. докстринг этого файла)."
    )


BRAIN_REPO_DIR = _resolve_brain_repo_dir()
CARDS_DIR = os.path.join(BRAIN_REPO_DIR, "02_Cards")


def detect_cluster(tags: list) -> str:
    cluster_map = {
        "одс": "ОДС", "ods": "ОДС",
        "агентная_ос": "Агентная ОС", "агент": "Агентная ОС",
        "граф_доверия": "Граф доверия", "доверие": "Граф доверия",
        "мышление": "Мышление",
    }
    for tag in tags:
        for key, cluster in cluster_map.items():
            if key in tag.lower():
                return cluster
    return "Без кластера"
