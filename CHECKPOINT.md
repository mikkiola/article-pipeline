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
- [x] `evidence_package/search_backend.py` экспортирует `search(query: str) -> list[SearchResult]`
- [x] Вся специфика Linkup инкапсулирована внутри файла (замена вендора = переписать только его)
- verify: `python3 -m py_compile evidence_package/search_backend.py && gitleaks detect --source evidence_package --no-git -v`
- done-when: файл компилируется; ручной вызов `search()` на тестовом запросе возвращает результат; `gitleaks` не находит ключа в коде
  - Подтверждено Ольгой вручную (BW_SESSION недоступна инструменту Claude Code):
    `search("test query linkup api smoke test")` → 20 результатов от живого
    Linkup API (не заглушка); первый результат — релевантный реальный
    GitHub-репозиторий. `py_compile`: PASS. `gitleaks`: 0 находок.
- status: done
- drift:
  - goal: 0.2 — goal drift caused by approved architecture change
    (D-024 pending formal write-up): `_get_api_key()` теперь читает
    только `LINKUP_API_KEY` из окружения, без обращения к `bw` изнутри
    файла. Written SPEC.md (строки 65-68, 204, 242-243) всё ещё
    специфицирует `bw get password ... --session $BW_SESSION` как
    механизм внутри скрипта — это честное расстояние от текущего
    письменного SPEC, не ошибка и не незапланированный дрейф.
    Остальная часть цели M2 (форма интерфейса `search()`,
    инкапсуляция специфики Linkup) — без отклонений. После формального
    внесения D-024 в SPEC.md (в конце сессии) эта же реализация
    оценивается как 0.0 против новой базовой линии.
  - constraint: 0.0 — ключ по-прежнему нигде не логируется/не
    печатается/не хардкодится; NFR#4 соблюдён.
  - scope: 0.0 — изменён только уже запланированный файл
    `search_backend.py`.
  - combined: 0.10 (0.2×0.5 + 0.0×0.3 + 0.0×0.2)

## M3: Driver-скрипт (Claims → запросы → бюджет → лог)
- [x] Читает Claims со `status: "claim"` из самого свежего `claim_extraction/output/pilot_run_*.json`
- [x] Формирует `search_query = novelty.value + basis.value`
- [x] Вызывает `search_backend.search()` с бюджетом 2 запроса/Claim, 20/прогон
- [x] Логирует сетевые ошибки и исчерпание бюджета, не прерывая прогон
- verify: `python3 -m py_compile evidence_package/*.py`
- done-when: сухой прогон на тестовых Claims не падает ни на сетевой ошибке, ни на исчерпании бюджета (оставшиеся Claims получают `pending`)
  - `evidence_package/driver.py` создан: `find_latest_pilot_run()`,
    `load_claims()`, `build_search_query()`, `run_searches()`.
    `MAX_REQUESTS_PER_CLAIM=2`, `MAX_REQUESTS_PER_RUN=20` — жёсткие
    константы в коде. Реальный запрос к Linkup в M3 не использовался —
    dry-run на 3 тестовых Claims со стаб-функцией `search_fn`
    (LINKUP_API_KEY не потребовался, бюджет не потрачен):
    1) успешный путь — 3/3 records, `status=None` (ждёт M4);
    2) сетевая ошибка (`RuntimeError` от стаба на всех 3) — прогон не
       упал, все 3 → `status="unverifiable"`, `requests_used=1`, event
       `search_error` в логе;
    3) исчерпание бюджета (`max_requests_per_run=1`, 3 Claims) — 1-й
       обработан, 2 оставшихся → `status="pending"`,
       `requests_used=0`, `search_budget_exhausted=True`.
    Все 3 сценария: PASS. Также проверена реальная загрузка (без
    вызова поиска): `find_latest_pilot_run()` находит
    `pilot_run_20260811T165911.json`, `load_claims()` — 5 Claims.
    `python3 -m py_compile evidence_package/*.py`: PASS. `gitleaks`:
    0 находок.
- status: done
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## M4: Интерактивная оценка Claude Code (status/source_url/license/note)
- [x] Для каждого Claim с результатами поиска — Claude Code в текущей сессии читает сниппеты/URL и присваивает `status`/`source_url`/`license`/`note`
- [x] Без отдельного LLM-вызова поверх результатов (D-015)
- verify: ручная проверка Ольгой на выборке записей — этот шаг интерактивный, скриптового verify для самой оценки нет
- done-when: каждый обработанный Claim получил `status` из `{verified, disputed, unverifiable, pending}` с полями по схеме `SPEC.md` (`source_url`/`license` присутствуют всегда, даже `null`)
  - Все 5 Claims оценены. Первый проход: 3× unverifiable, 2× verified
    (claim_03 — Habr, claim_04 — vc.ru). Retry не использовался ни для
    одного Claim: `retry_search()` переиспользует тот же
    `search_query` (SPEC не допускает менять формулу запроса между
    попытками), а низкая релевантность у claim_01/02/05 — структурная
    (диффузный запрос), не случайный сбой, который повтор мог бы
    исправить.
  - Построчная проверка Ольгой (сверка полных текстов атомов и полных
    страниц источников — не только сниппетов) понизила обе `verified`-
    записи до `unverifiable`: claim_03 — источник иллюстрирует тот же
    абстрактный паттерн на другом материале (LLM-документация), не
    подтверждает тезис в домене атома (граф доверия/ОДС); claim_04 —
    источник оказался статьёй AI-персоны (Digital Author Persona), не
    верифицируемым человеческим экспертом, что не даёт независимого
    эпистемического подтверждения даже при совпадении домена. Итог:
    **5 из 5 → unverifiable**, `source_url`/`license` — `null` явно у
    всех пяти.
  - `retry_search()` добавлена в `driver.py`: enforcement per-Claim
    (`MAX_REQUESTS_PER_CLAIM=2`) и run-wide (`MAX_REQUESTS_PER_RUN=20`)
    бюджетов через `raise SearchBudgetError`, не молчаливое
    превышение. Проверено на стабах: успешный retry, превышение
    per-Claim кэпа, превышение run-wide кэпа — все 3 сценария PASS.
- status: done
- drift:
  - goal: 0.0
  - constraint: 0.0
  - scope: 0.0
  - combined: 0.0

## M5: Запись evidence_run/evidence_log (Immutable Lineage)
- [x] `evidence_package/output/evidence_run_<timestamp>.json`
- [x] `evidence_package/output/evidence_log_<timestamp>.json`
- [x] Коллизия `run_id` (совпадение timestamp) — `raise error`, не перезапись
- verify: `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('evidence_package/output/evidence_*.json')]"`
- done-when: оба файла валидный JSON и записаны; повторный запуск с тем же `run_id` падает с ошибкой, а не перезаписывает
  - `evidence_package/write_evidence.py` создан (`build_evidence_run()`,
    `build_evidence_log()`, `write_outputs()`), тот же паттерн, что
    `build_pilot_output.py` в Claim Extraction. `run_id=20260813T114717`
    (тот же run_id, что у поисковой фазы M3/M4 — единый логический
    прогон).
  - Прогон 1 (первая запись): SUCCESS —
    `evidence_run_20260813T114717.json` (5 записей, все `unverifiable`),
    `evidence_log_20260813T114717.json` (`status_counts.unverifiable=5`,
    `requests_used_total=5`, `search_budget_exhausted=false`).
  - Прогон 2 (тот же `run_id` намеренно повторно): `FileExistsError` —
    "evidence_run_20260813T114717.json уже существует — Immutable
    Lineage запрещает перезапись прежнего прогона." Файлы прогона 1 не
    тронуты (mtime не изменился после попытки коллизии).
  - `python3 -c "import json,glob; ..."`: PASS (оба файла валидный
    JSON). `gitleaks`: 0 находок.
  - Staging-файл `_m4_staging_20260813T114717.json` (сырые результаты
    поиска M4) не коммитится — добавлен в `.gitignore`, не часть
    канонической схемы вывода SPEC.md.
- status: done
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
