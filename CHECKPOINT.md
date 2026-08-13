# CHECKPOINT — Evidence Package (Article Pipeline, Фаза 2)

Milestones перенесены из `SPEC.md` (коммит `2fe0aac`). Drift измеряется
по [[~/.claude/rules/drift-control.md]] — 3 оси (goal/constraint/scope),
combined = goal×50% + constraint×30% + scope×20%. Обновлять `status` и
`drift` по ходу реализации, не только в конце.

## M1: Установить linkup-sdk и настроить чтение LINKUP_API_KEY
- [x] `pip install linkup-sdk`
- [x] Подтвердить запись `linkup-api-key-article-pipeline` в Bitwarden
- [x] Проверить чтение ключа: `bw get password linkup-api-key-article-pipeline --session $BW_SESSION`
- verify: `pip show linkup-sdk && bw get password linkup-api-key-article-pipeline --session $BW_SESSION | wc -c`
- done-when: `linkup-sdk` установлен; команда `bw get password` возвращает непустой вывод (сам ключ в лог/вывод команды verify не печатать)
- status: done
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## M2: search_backend.py (swappable interface, реализация на Linkup)
- [ ] `evidence_package/search_backend.py` экспортирует `search(query: str) -> list[SearchResult]`
- [ ] Вся специфика Linkup инкапсулирована внутри файла (замена вендора = переписать только его)
- verify: `python3 -m py_compile evidence_package/search_backend.py && gitleaks detect --source evidence_package --no-git -v`
- done-when: файл компилируется; ручной вызов `search()` на тестовом запросе возвращает результат; `gitleaks` не находит ключа в коде
- status: not-started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## M3: Driver-скрипт (Claims → запросы → бюджет → лог)
- [ ] Читает Claims со `status: "claim"` из самого свежего `claim_extraction/output/pilot_run_*.json`
- [ ] Формирует `search_query = novelty.value + basis.value`
- [ ] Вызывает `search_backend.search()` с бюджетом 2 запроса/Claim, 20/прогон
- [ ] Логирует сетевые ошибки и исчерпание бюджета, не прерывая прогон
- verify: `python3 -m py_compile evidence_package/*.py`
- done-when: сухой прогон на тестовых Claims не падает ни на сетевой ошибке, ни на исчерпании бюджета (оставшиеся Claims получают `pending`)
- status: not-started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## M4: Интерактивная оценка Claude Code (status/source_url/license/note)
- [ ] Для каждого Claim с результатами поиска — Claude Code в текущей сессии читает сниппеты/URL и присваивает `status`/`source_url`/`license`/`note`
- [ ] Без отдельного LLM-вызова поверх результатов (D-015)
- verify: ручная проверка Ольгой на выборке записей — этот шаг интерактивный, скриптового verify для самой оценки нет
- done-when: каждый обработанный Claim получил `status` из `{verified, disputed, unverifiable, pending}` с полями по схеме `SPEC.md` (`source_url`/`license` присутствуют всегда, даже `null`)
- status: not-started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## M5: Запись evidence_run/evidence_log (Immutable Lineage)
- [ ] `evidence_package/output/evidence_run_<timestamp>.json`
- [ ] `evidence_package/output/evidence_log_<timestamp>.json`
- [ ] Коллизия `run_id` (совпадение timestamp) — `raise error`, не перезапись
- verify: `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('evidence_package/output/evidence_*.json')]"`
- done-when: оба файла валидный JSON и записаны; повторный запуск с тем же `run_id` падает с ошибкой, а не перезаписывает
- status: not-started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## M6: Передать Ольге на ручную построчную оценку
- [ ] Краткое резюме прогона (счётчики по `status`, флаг `search_budget_exhausted`) + путь к `evidence_run_*.json`
- verify: — (человеческий шаг, не автоматизируется)
- done-when: Ольга подтвердила получение материала для оценки
- status: not-started
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0
