"""
Atom Selector — Article Pipeline.

Выбирает один атом графа (02_Cards/) для статьи, с ротацией по кластерам
(round-robin). Не реализует Collision Engine — это отдельная зона Drift
(agent.py), не трогается.

Переиспользует detect_cluster() и CARDS_DIR из graph_reader.py — общей
утилиты, вынесенной из agent.py, чтобы устранить прямую зависимость
Article Pipeline от Drift (см. TASK 1, D-014).

Состояние: atom_selector_state.json, рядом с этим файлом.
Отдельно от state.json Drift (см. CONSTITUTION_ap: новый state — отдельный
файл от state.json Drift).

Копия из brain.git (локальный чекаут brain.git — см. graph_reader.py,
BRAIN_REPO_DIR), коммиты bd7b784 ("feat: Atom Selector") и 97b87f7
("fix: atom_selector — не падать на нечитаемом файле карточки"). Скопирована
для пилота Claim Extraction (SPEC.md, Article Pipeline) без изменений логики —
может разойтись с оригиналом, синхронизировать вручную при изменениях в
brain.git.
"""

import os
import re
import json
import random
from pathlib import Path
from datetime import datetime

import graph_reader

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atom_selector_state.json")

# Фиксированный порядок ротации — не менять между запусками без явного [ЗАПРОС]
CLUSTERS = ["Граф доверия", "Агентная ОС", "Мышление", "ОДС"]


def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"last_cluster_index": -1, "last_run_at": None}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _extract_tags(file_path: str) -> list:
    """
    Извлекает теги атома из YAML frontmatter или inline #тегов.
    Минимальная реализация — уточнить при первом реальном прогоне против
    формата карточек 02_Cards/ (открытый пункт, см. design.md "Не закрыто").
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError, OSError) as e:
        print(f"[atom_selector] Пропуск файла '{file_path}': не читается ({e})")
        return []
    tags = re.findall(r"#([\w\-/]+)", content)
    return tags


def _atoms_in_cluster(cluster_name: str) -> list:
    """Возвращает список путей файлов 02_Cards/, чей detect_cluster() == cluster_name."""
    result = []
    cards_dir = Path(graph_reader.CARDS_DIR)
    for file_path in cards_dir.glob("*.md"):
        tags = _extract_tags(str(file_path))
        if graph_reader.detect_cluster(tags) == cluster_name:
            result.append(str(file_path))
    return result


def select_atom() -> dict:
    """
    Выбирает один атом с ротацией по кластерам.

    Возвращает:
        {"cluster": str, "atom_path": str, "atom_text": str}

    Бросает RuntimeError, если ни один из 4 кластеров не дал атома
    после фильтров (все кластеры пусты за один прогон).
    """
    state = _load_state()
    idx = state.get("last_cluster_index", -1)

    attempts = 0
    while attempts < len(CLUSTERS):
        idx = (idx + 1) % len(CLUSTERS)
        cluster = CLUSTERS[idx]
        atoms = _atoms_in_cluster(cluster)

        if atoms:
            atom_path = random.choice(atoms)
            with open(atom_path, "r", encoding="utf-8") as f:
                atom_text = f.read()

            _save_state({
                "last_cluster_index": idx,
                "last_run_at": datetime.now().isoformat(),
            })

            return {
                "cluster": cluster,
                "atom_path": atom_path,
                "atom_text": atom_text,
            }

        # Пусто в этом кластере — залогировать пропуск, идти к следующему
        print(f"[atom_selector] Пропуск кластера '{cluster}': атомов нет после фильтра")
        attempts += 1

    raise RuntimeError(
        "Atom Selector: ни один из 4 кластеров не дал атома после фильтров. "
        "Публикация невозможна на этом прогоне."
    )


if __name__ == "__main__":
    result = select_atom()
    print(f"Кластер: {result['cluster']}")
    print(f"Атом: {result['atom_path']}")
