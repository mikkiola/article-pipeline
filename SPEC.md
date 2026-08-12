# Evidence Package — пилот (Article Pipeline, Фаза 2)

## Overview

Второй живой компонент конвейера после Claim Extraction: для 5-10 Claims из
уже существующих `pilot_run_*.json` найти внешний источник через Linkup
Search API, оценить его отношение к Claim (verified/disputed/unverifiable/
pending) и зафиксировать тип лицензии источника, прежде чем проектировать
Strategy Layer и остальной конвейер под это.

## Goals

- [ ] Взять 5-10 Claims со `status: "claim"` из последнего по времени
      `claim_extraction/output/pilot_run_*.json`
- [ ] Для каждого Claim сформировать поисковый запрос из `novelty` + `basis`
      и выполнить поиск через Linkup за swappable-интерфейсом
      (`search_backend.py`)
- [ ] Соблюсти жёсткий бюджет запросов: максимум 2 на Claim, максимум 20 на
      весь прогон
- [ ] Дать Claude Code интерактивно оценить найденные результаты и
      присвоить `status`, `source_url`, `license` для каждого Claim — без
      отдельного LLM-вызова поверх результатов поиска (D-015, никакого
      cross-model verification loop)
- [ ] Зафиксировать факт и время попытки верификации (`searched_at`)
      отдельно от `status` — обязательное поле первой версии схемы,
      иначе `pending` и `unverifiable` неразличимы на уровне данных
- [ ] Immutable Lineage: `evidence_run_<timestamp>.json` +
      `evidence_log_<timestamp>.json`, коллизия `run_id` (timestamp) —
      ошибка, не перезапись
- [ ] Дать Ольге материал для ручной построчной оценки каждой
      Evidence-записи — как и в Claim Extraction, формального числового
      критерия успеха пилота нет

## Явно не входит в этот пилот

- Strategy Layer, Author, Quality Gate, Platform Adapter, Experiment Log —
  следующие звенья конвейера, не эта задача.
- Полный прогон по всем существующим Claims — только пилот на подмножестве
  5-10.
- Интеграция с `obsidian-local-rest-api` — канал решён (D-022) для будущего
  использования конвейером в целом, но не требуется этому конкретному
  компоненту; Evidence Package работает только с локальными JSON-файлами
  Claim Extraction.
- Числовой confidence score для Evidence — намеренно только enum-статус
  (`verified`/`disputed`/`unverifiable`/`pending`), без числа и без
  автокалибровки, по прямому требованию (в отличие от D-008, который про
  числовой confidence в Claim Extraction — сюда этот паттерн не переносится).
- Автоматическая эвристика, присваивающая `status`/`license` без участия
  интерактивной сессии Claude Code — явно отклонено.
- Миграция `atom_selector.py`/`graph_reader.py` в единый источник, перевод
  файлов Claim Extraction на английский, приватность
  `pilot_log_20260811T115831.json` — отдельные задачи, не в этой сессии.

## Tech Stack

- Python 3, официальный `linkup-sdk` (`pip install linkup-sdk`; зависимости
  `httpx`, `pydantic`; Python 3.9+, ~300k загрузок/мес,
  [LinkupPlatform/linkup-python-sdk](https://github.com/LinkupPlatform/linkup-python-sdk))
  как реализация поиска внутри `search_backend.py` — не самодельный
  HTTP-клиент.
- **Swappable search interface**: `evidence_package/search_backend.py`
  экспортирует одну функцию `search(query: str) -> list[SearchResult]`. Вся
  специфика Linkup инкапсулирована внутри этого файла; замена вендора в
  будущем — переписать только его, не драйвер-скрипт и не схему Evidence.
- **LINKUP_API_KEY** хранится в Bitwarden, запись
  `linkup-api-key-article-pipeline`. Скрипт получает ключ вызовом:
  ```
  bw get password linkup-api-key-article-pipeline --session $BW_SESSION
  ```
  Сессию (`bw login` / `bw unlock`, экспорт `BW_SESSION`) Ольга открывает
  вручную перед запуском — скрипт никогда не хранит и не логирует сам
  ключ. Не `.env`, не macOS Keychain (Keychain в этом проекте зарезервирован
  под ключи самого Bitwarden, а не под рабочие токены — см. CONSTITUTION_ap).
- Bitwarden CLI `bitwarden-cli` (2026.7.0) установлен через Homebrew в этой
  сессии; авторизацию (`bw login`) выполняет Ольга вручную — вне периметра
  задач, которые может делать Claude Code без ввода мастер-пароля/2FA.

## Расположение кода

`mikkiola/article-pipeline/evidence_package/` (пустой каркас, D-014), по
аналогии с `claim_extraction/`. В отличие от Claim Extraction, копирования
зависимостей из `brain.git` здесь не требуется — Evidence Package не
работает с `02_Cards/` напрямую, только с уже существующими
`claim_extraction/output/pilot_run_*.json`.

## Detailed Requirements

### Functional Requirements

**1. Отбор Claims для пилота**

Скрипт читает **самый свежий по timestamp** файл
`claim_extraction/output/pilot_run_*.json`, отбирает записи со
`status: "claim"` (записи `no_claim` исключаются — там нет утверждения,
которое можно проверять), берёт до 10 штук. Если в самом свежем файле
Claims со `status: "claim"` меньше 5 — это фиксируется в
`evidence_log_*.json` как наблюдение, прогон не падает (см. D-013-style
осторожность: не выдумывать порог, которого нет в каноне).

**2. Формирование поискового запроса**

`search_query = f"{novelty.value} {basis.value}"` — только текст полей
`novelty` и `basis` (само проверяемое утверждение), без меток
`[ФАКТ]`/`[ГИПОТЕЗА]` и без `audience`/`belief_changed`/`desired_action` —
эти три поля не несут проверяемого факта, а несут стратегию воздействия.

**3. Вызов Linkup и бюджет**

`search_backend.search(query)` вызывается до 2 раз на Claim (вторая попытка
только если первая не дала результата с достаточной релевантностью — решает
интерактивная сессия, не скрипт). Жёсткий лимит на весь прогон — 20
запросов суммарно; при достижении лимита прогон **не падает**, оставшиеся
необработанные Claims получают `status: "pending"`, `requests_used: 0`, и в
`evidence_log_*.json` пишется явный флаг `search_budget_exhausted: true`.

**4. Интерактивная оценка Claude Code**

Для каждого Claim с результатами поиска Claude Code в текущей сессии читает
`search_query` и возвращённые сниппеты/URL, и вручную присваивает:
`status`, `source_url`, `source_title`, `license`, `note`. Никакого
отдельного API-вызова к модели для этой оценки — та же интерактивная
сессия, что делает и запрос к Linkup видимым для аудита (D-015).

**5. Схема Evidence record**

Одна запись на Claim (JSON):

```json
{
  "evidence_id": "20260812T160000_01",
  "run_id": "20260812T160000",
  "created_at": "2026-08-12T16:00:00+03:00",
  "claim_id": "20260811T153000_01",
  "status": "verified",
  "searched_at": "2026-08-12T16:00:05+03:00",
  "search_query": "novelty-текст basis-текст",
  "requests_used": 1,
  "source_url": "https://example.com/article",
  "source_title": "...",
  "license": "cc_by",
  "note": null
}
```

Поля:
- `evidence_id` — `"{run_timestamp}_{порядковый номер в прогоне}"`, тот же
  паттерн, что `claim_id` в Claim Extraction.
- `claim_id` — обязательный бэклинк на запись в `pilot_run_*.json`
  (аналог `atom_path` у Claim), не опционален.
- `status` — один из `verified` / `disputed` / `unverifiable` / `pending`.
  Никакого числового confidence.
- `searched_at` — ISO 8601 или `null`. `null` означает "попытка ещё не
  предпринята" (`pending`, включая случай исчерпанного бюджета);
  непустое значение означает "попытка была", независимо от исхода —
  это единственное поле, отличающее `pending` от `unverifiable` на уровне
  данных, а не только по тексту `status`.
- `source_url`, `license` — **присутствуют как поля всегда**, даже когда
  источник не найден: тогда оба `null`, явно, а не отсутствующие ключи.
  Правило "каждый факт несёт source + license" применяется буквально к
  `verified`/`disputed` (там оба поля заполнены содержательно); для
  `unverifiable`/`pending` `null` — это не нарушение правила, а его честная
  фиксация ("искали и не нашли" видно по `searched_at`, а не по
  умолчанию).
- `license` — одно из `public_domain` / `cc_by` / `cc_by_sa` /
  `all_rights_reserved` / `unknown`. `unknown` — источник найден, но тип
  лицензии определить не удалось (это не то же самое, что `null` при
  `unverifiable`, где источника вообще нет).
- `note` — короткий свободный текст. Обязателен при `disputed` (в чём
  противоречие) и при `unverifiable` (почему не засчитано), опционален при
  `verified`/`pending`.
- `requests_used` — сколько запросов Linkup потрачено на этот Claim (0-2),
  для аудита бюджета.

**6. Файлы вывода (Immutable Lineage, D-011)**

- `evidence_package/output/evidence_run_<timestamp>.json` — массив Evidence
  record'ов за один прогон. Новый прогон = новый файл, никогда не
  перезаписывает предыдущий.
- `evidence_package/output/evidence_log_<timestamp>.json` — по аналогии с
  `pilot_log` в Claim Extraction: события ошибок/таймаутов Linkup, сводка
  по `status` (счётчики verified/disputed/unverifiable/pending), суммарное
  использование бюджета запросов, флаг `search_budget_exhausted`.
- `run_id` = timestamp прогона. Повторный запуск с тем же `run_id`
  (совпадение timestamp) — **ошибка**, не перезапись, тот же принцип, что
  в Claim Extraction.

**7. Обработка сетевых ошибок**

Таймаут/ошибка на одном запросе к Linkup логируется в
`evidence_log_*.json`, соответствующий Claim получает `status:
"unverifiable"` с `note`, объясняющей сетевой сбой, и прогон продолжается
следующим Claim — весь прогон не падает из-за одной проблемной попытки
(тот же принцип устойчивости, что `_extract_tags()` в `atom_selector.py`).

### Non-Functional Requirements

1. Ни одна сетевая ошибка/таймаут по одному Claim не должна ронять весь
   прогон.
2. Бюджет запросов — жёсткие константы в коде (`max_requests_per_claim =
   2`, `max_requests_per_run = 20`), с комментарием-источником решения (по
   аналогии с порогом D-008 — явное число, не "например").
3. Immutable Lineage: `evidence_run_*.json` и `evidence_log_*.json`
   никогда не перезаписываются; коллизия `run_id` — `raise error`.
4. `LINKUP_API_KEY` никогда не появляется в логах, коде или выводе —
   только в памяти процесса на время прогона, полученный через `bw CLI`.
5. Backlink Evidence → Claim (`claim_id`) обязателен, не опционален.
6. `source_url`/`license` — поля присутствуют всегда, даже `null`, не
   отсутствующие ключи (см. схему выше).

## Security Considerations

Единственный новый секрет в этом пилоте — `LINKUP_API_KEY`, хранится
исключительно в Bitwarden (запись `linkup-api-key-article-pipeline`), не в
`.env`, не в системной связке ключей macOS (она зарезервирована под ключи
самого Bitwarden). Скрипт получает ключ через `bw CLI` с явной,
Ольгой открытой сессией (`$BW_SESSION`), не хранит его на диске и не
логирует.

Это первый компонент конвейера с реальным исходящим сетевым вызовом на
платный сторонний API (Linkup, ~$20/мес) — в отличие от Claim Extraction,
где не было ни сети, ни секрета. Жёсткий лимит 20 запросов на прогон —
защита от случайного перерасхода бюджета при баге или зацикливании.

Git-операции на запись — только через Claude Code, не через другие
инструменты (тот же принцип, что в Claim Extraction).

## Test Plan

- **Технический минимум**: скрипт проходит 5-10 Claims без необработанных
  падений; сетевые ошибки логируются и не прерывают прогон; лимит 20
  запросов/прогон корректно останавливает дальнейший поиск (оставшиеся
  Claims получают `pending`, не крашат прогон); `evidence_run_*.json` и
  `evidence_log_*.json` записываются корректно и не перезаписывают файлы
  предыдущих прогонов; коллизия `run_id` — ошибка.
- **Приёмка по содержанию — формального числового порога нет**, как и в
  Claim Extraction. Ольга вручную читает и оценивает каждую Evidence-запись
  — разумны ли `status`/`source_url`/`license` для соответствующего Claim.

## Milestones

1. [ ] Установить `linkup-sdk` (`pip install linkup-sdk`); подтвердить, что
       запись `linkup-api-key-article-pipeline` в Bitwarden создана и
       читается через `bw get password ... --session $BW_SESSION`.
2. [ ] Написать `search_backend.py` (swappable interface, реализация на
       Linkup).
3. [ ] Написать driver-скрипт: читает Claims из последнего `pilot_run_*.json`,
       формирует запросы, вызывает `search_backend` с бюджетом 2/Claim,
       20/прогон, логирует ошибки и использование бюджета.
4. [ ] Для каждого Claim с результатами поиска — интерактивная оценка
       Claude Code: `status`/`source_url`/`license`/`note`.
5. [ ] Записать `evidence_run_<timestamp>.json` и
       `evidence_log_<timestamp>.json`.
6. [ ] Передать Ольге для ручной построчной оценки каждой Evidence-записи.

## Open Questions / Decisions Needed

Технические детали, которые решены как автор реализации (не как молчаливый
выбор архитектуры) — стоит подтвердить или поправить при чтении этого
SPEC, до реализации:

- Источник Claims для пилота — **самый свежий по timestamp**
  `pilot_run_*.json`, только записи со `status: "claim"`. Если в
  Claim Extraction было несколько прогонов и нужен конкретный из них (не
  последний) — уточнить.
- `search_query` = конкатенация текста `novelty` + `basis` без меток
  `[ФАКТ]`/`[ГИПОТЕЗА]` и без остальных трёх полей Claim.
- `license: "unknown"` (источник найден, лицензия не определена) отличается
  от `license: null` при `unverifiable` (источника вообще нет) — эта
  граница зафиксирована в схеме выше, стоит явно подтвердить, что это
  верное прочтение.
- Вторая попытка поиска (2-й из 2 разрешённых запросов на Claim)
  выполняется только если первая не дала достаточно релевантного
  результата — решение принимает интерактивная сессия Claude Code в
  моменте, не формализованный порог релевантности в коде.

---

Спецификация готова. Начать реализацию можно новой сессией командой:

```
Read SPEC.md and start implementation
```

После реализации — проверка:
```
/spec-verify
```
