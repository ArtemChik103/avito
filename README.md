# Avito Services Splitter

Локальный MVP для кейса split одного объявления на несколько самостоятельных услуг. Репозиторий содержит backend на FastAPI, demo frontend на Streamlit, локальные launcher-скрипты, набор regression/evaluation датасетов и browser smoke-test на Playwright.

## Что Уже Готово

На текущий момент в проекте реализовано:

- backend pipeline для детерминированного split-анализа без внешних API
- FastAPI API с `POST /split` и `GET /health`
- Streamlit demo UI для ручной проверки сценариев
- launcher-скрипты для запуска backend + frontend одной командой
- unit, integration и API tests на `pytest`
- browser smoke e2e test на Playwright + локальном Chrome
- regression coverage по локальным case-файлам
- audit и regression-прогон экспертного датасета `rnc_dataset_markup.json/.csv`

## Структура Репозитория

- [src/avito_splitter](src/avito_splitter) - доменная логика, API, evaluation и audit
- [demo](demo) - Streamlit demo UI и demo-кейсы
- [data](data) - runtime-каталог и локальные regression датасеты
- [tests](tests) - unit, integration, API, Streamlit smoke и Playwright smoke tests
- [run_project.py](run_project.py), [run_project.bat](run_project.bat) - локальный запуск проекта
- [rnc_dataset_markup.json](rnc_dataset_markup.json), [rnc_dataset_markup.csv](rnc_dataset_markup.csv) - экспертный датасет

## Архитектура

Поток обработки выглядит так:

1. Клиент отправляет объявление в формате `AdInput`.
2. Backend нормализует текст и разбивает его на предложения и clauses.
3. Extractor находит микрокатегории по `matchPhrases` и лемматизированным вариантам.
4. Independence analyzer определяет для каждого evidence статус `blocked`, `confirmed` или `neutral`.
5. Pipeline агрегирует решение по микрокатегориям, исключает исходный `mcId` и собирает `SplitResponse`.
6. Draft generator строит детерминированные тексты черновиков.
7. Streamlit UI показывает verdict, drafts и raw JSON.

Ключевые точки в коде:

- API: [api.py](src/avito_splitter/api.py)
- pipeline: [pipeline.py](src/avito_splitter/pipeline.py)
- preprocessing: [preprocessing.py](src/avito_splitter/preprocessing.py)
- category extraction: [category_extractor.py](src/avito_splitter/category_extractor.py)
- independence analysis: [independence_analyzer.py](src/avito_splitter/independence_analyzer.py)
- draft generation: [draft_generator.py](src/avito_splitter/draft_generator.py)
- Streamlit UI: [streamlit_app.py](demo/streamlit_app.py)

## Публичный Контракт

Вход API:

```json
{
  "itemId": 5002,
  "mcId": 101,
  "mcTitle": "Ремонт квартир и домов под ключ",
  "description": "Делаем ремонт квартир под ключ, а также отдельно выполняем сантехнические и электромонтажные работы."
}
```

Выход API:

```json
{
  "shouldSplit": true,
  "drafts": [
    {
      "mcId": 102,
      "mcTitle": "Сантехника",
      "text": "..."
    },
    {
      "mcId": 103,
      "mcTitle": "Электрика",
      "text": "..."
    }
  ]
}
```

Стабильные правила:

- один `mcId` порождает не более одного `draft`
- исходный `item.mcId` не попадает в `drafts`
- `drafts` всегда список, даже если он пустой
- порядок `drafts` соответствует первому подтвержденному появлению услуги в тексте
- bare mention без подтверждающего контекста не создает `draft`

## Данные

Основные файлы данных:

- [data/microcategories.raw.json](data/microcategories.raw.json) - базовый локальный словарь микрокатегорий
- [data/microcategories.enriched.json](data/microcategories.enriched.json) - runtime-словарь с `matchPhrases` и `draftLead`
- [data/gold_examples.json](data/gold_examples.json) - базовые regression-кейсы
- [data/synthetic_eval_examples.json](data/synthetic_eval_examples.json) - расширенный synthetic eval-набор
- [demo/demo_cases.json](demo/demo_cases.json) - сценарии для demo UI
- [rnc_dataset_markup.json](rnc_dataset_markup.json) и [rnc_dataset_markup.csv](rnc_dataset_markup.csv) - экспертный датасет

Текущее состояние экспертного датасета:

- `2480` строк в `json`
- `2480` строк в `csv`
- `json/csv` консистентны по содержимому
- найдена одна структурная аномалия: у JSON-строки с индексом `318` `itemId` нечисловой

## Быстрый Запуск

Если окружение уже подготовлено, самый короткий запуск:

```powershell
python run_project.py
```

На Windows можно так:

```bat
run_project.bat
```

Launcher поднимет:

- FastAPI backend
- Streamlit demo UI

После старта открой:

- `http://127.0.0.1:8501` - demo UI
- `http://127.0.0.1:8000/docs` - Swagger / OpenAPI

Если порты заняты, launcher сам выберет следующие свободные и напечатает их в терминале.

## Подготовка Чистой Машины

Минимально нужно:

- `Git`
- `Python 3.10+`
- локальный `Google Chrome` для Playwright smoke-test

### Проверка Базовых Инструментов

В PowerShell:

```powershell
git --version
python --version
```

Для Chrome:

```powershell
Test-Path "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

### Первичная Установка Зависимостей

После `git clone`:

```powershell
cd avito
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Этого достаточно для backend, Streamlit UI, `pytest` и Playwright-библиотеки.

## Варианты Запуска

### Вариант 1. Один Командный Запуск

- Python: `python run_project.py`
- Windows batch: `run_project.bat`

Что делает launcher:

- поднимает `uvicorn` на свободном локальном порту
- поднимает `streamlit run demo/streamlit_app.py`
- автоматически пробрасывает `AVITO_BACKEND_URL` во frontend
- открывает browser, если не указан `--no-browser`
- останавливает оба процесса по `Ctrl+C`

### Вариант 2. Раздельный Ручной Запуск

Backend:

```powershell
uvicorn src.avito_splitter.api:app --reload
```

Frontend:

```powershell
streamlit run demo/streamlit_app.py
```

Если backend запущен не на `8000`, укажи другой `URL backend` в sidebar Streamlit.

### Вариант 3. Только Backend

```powershell
python run_project.py backend
```

### Вариант 4. Только Frontend

```powershell
python run_project.py frontend
```

## Demo UI

Форма в demo UI поддерживает:

- `itemId`
- выбор исходной микрокатегории из dropdown
- автоматическую синхронизацию `mcId`
- ввод `description`
- подстановку готовых demo-кейсов
- сравнение ответа backend с ожидаемым эталоном demo-кейса

Основные demo-сценарии лежат в [demo/demo_cases.json](demo/demo_cases.json):

- комплексная услуга
- отдельные услуги
- перечисление услуг
- исключение исходной категории
- нейтральное упоминание
- смешанный контекст

## Ручная Проверка

Полезные примеры для быстрой ручной проверки:

1. Без split:

```text
Делаем ремонт под ключ, включая электрику и сантехнику.
```

Ожидание:

- `shouldSplit = false`
- `drafts = []`

2. Split на 2 услуги:

```text
Отдельно выполняем сантехнические и электромонтажные работы.
```

Ожидание:

- `shouldSplit = true`
- `draftMcIds = [102, 103]`

3. Перечисление услуг:

```text
Выполняем электрику, сантехнику, натяжные потолки.
```

Ожидание:

- `shouldSplit = true`
- `draftMcIds = [103, 102, 104]`

4. Нейтральное упоминание:

```text
Делаем электрику и сантехнику в квартирах и домах.
```

Ожидание:

- `shouldSplit = false`
- `drafts = []`

## Автоматические Проверки

### Полный Локальный Прогон

```powershell
pytest
```

На текущий момент полный тестовый набор:

- backend unit tests
- pipeline regression
- FastAPI API tests
- Streamlit in-process smoke tests
- Playwright e2e smoke test в реальном Chrome
- audit/regression тесты по экспертному датасету

### Отдельные Полезные Команды

Все локальные кейсы:

```powershell
python run_project.py report
```

Synthetic evaluation:

```powershell
python -c "from pathlib import Path; from src.avito_splitter.evaluation import evaluate_file; print(evaluate_file(Path('data/synthetic_eval_examples.json')))"
```

Expert dataset audit:

```powershell
python -m src.avito_splitter.expert_dataset_audit
```

Playwright browser smoke:

```powershell
pytest tests/test_playwright_e2e.py
```

## Покрытие Проверок

Ключевые test files:

- [test_preprocessing.py](tests/test_preprocessing.py)
- [test_category_extractor.py](tests/test_category_extractor.py)
- [test_independence_analyzer.py](tests/test_independence_analyzer.py)
- [test_draft_generator.py](tests/test_draft_generator.py)
- [test_pipeline.py](tests/test_pipeline.py)
- [test_api.py](tests/test_api.py)
- [test_all_case_files.py](tests/test_all_case_files.py)
- [test_evaluation.py](tests/test_evaluation.py)
- [test_expert_dataset_audit.py](tests/test_expert_dataset_audit.py)
- [test_streamlit_smoke.py](tests/test_streamlit_smoke.py)
- [test_playwright_e2e.py](tests/test_playwright_e2e.py)

Что закрыто автоматикой:

- blocking-context против split
- confirmed / neutral / mixed scenarios
- исключение исходной категории
- порядок `drafts`
- дедупликация категорий
- API contract
- Streamlit form flow
- реальный browser smoke на живом backend/frontend
- экспертный dataset regression

## Как Проверять Проект Экспертам

Самый короткий маршрут проверки:

1. Выполнить `python -m pip install -r requirements.txt`
2. Выполнить `pytest`
3. Выполнить `python run_project.py`
4. Открыть demo UI в браузере
5. Подставить demo-кейсы и проверить verdict
6. При необходимости открыть `/docs` и проверить контракт `POST /split`
7. Выполнить `python -m src.avito_splitter.expert_dataset_audit`

## Операционные Замечания

- проект не использует внешние API для split-логики
- backend полностью локальный и синхронный
- Streamlit является thin client и не содержит доменной логики split
- если launcher сообщает о занятом порте, это нормальное поведение: он автоматически выберет свободный
- для Playwright e2e нужен локально установленный Chrome
