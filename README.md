# Avito Services Splitter

Локальный MVP для split одного объявления на несколько самостоятельных услуг. В проекте backend на FastAPI сохранен без изменений, а demo frontend переведен на Gradio и работает как thin client поверх `POST /split`.

## Что В Репозитории

- текущий публичный Gradio demo: https://2cb0fcbccca842137d.gradio.live
- backend API на FastAPI с `POST /split` и `GET /health`
- детерминированный split-pipeline без внешних API
- demo frontend на Gradio
- launcher-скрипты для локального и публичного demo
- regression, API, smoke и browser e2e тесты на `pytest` + Playwright
- локальные данные и demo cases

## Структура

- [src/avito_splitter](src/avito_splitter) - API и доменная логика
- [demo/gradio_app.py](demo/gradio_app.py) - Gradio demo UI
- [demo/demo_cases.json](demo/demo_cases.json) - demo-кейсы
- [data](data) - runtime-каталог и eval-данные
- [tests](tests) - unit, API, smoke и Playwright e2e
- [run_project.py](run_project.py) - основной launcher
- [run_project.bat](run_project.bat) - thin wrapper над launcher
- [start_demo.bat](start_demo.bat) - быстрый запуск demo на Windows

## Архитектура

Поток обработки:

1. Gradio UI собирает payload объявления.
2. Frontend отправляет HTTP-запрос в backend `POST /split`.
3. Backend нормализует текст, находит микрокатегории и проверяет самостоятельность услуги.
4. Pipeline возвращает `SplitResponse`.
5. Gradio UI показывает verdict, drafts, raw JSON и сверку с эталоном demo-case.

Gradio не содержит split-логики. Он только загружает demo-cases и каталог микрокатегорий, вызывает backend и рендерит ответ.

## Публичный Контракт API

Вход:

```json
{
  "itemId": 1002,
  "mcId": 101,
  "mcTitle": "Ремонт квартир и домов под ключ",
  "description": "Отдельно выполняем сантехнические и электромонтажные работы."
}
```

Выход:

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

- backend API не менялся при миграции frontend
- исходный `mcId` не попадает в `drafts`
- `drafts` всегда список
- порядок `drafts` соответствует порядку подтвержденных услуг в тексте

## Установка

Минимально нужно:

- `Python 3.10+`
- `Git`
- локальный `Google Chrome` для Playwright smoke-test

Установка:

```powershell
cd avito
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

В `requirements.txt` demo frontend теперь зависит от `gradio`. `streamlit` больше не используется.

## Быстрый Запуск

Самый короткий локальный запуск:

```powershell
python run_project.py
```

Или на Windows:

```bat
run_project.bat
```

Для совсем быстрого локального старта demo:

```bat
start_demo.bat
```

Launcher поднимет:

- FastAPI backend
- локальный Gradio demo UI

Если порты заняты, launcher автоматически выберет следующие свободные порты и напечатает итоговые ссылки.

## Команды Launcher

### Локальный demo

```powershell
python run_project.py
python run_project.py demo
```

Что делает:

- поднимает backend
- поднимает локальный Gradio frontend
- ждет `GET /health` у backend и `GET /` у frontend
- печатает локальные ссылки

### Публичный demo

```powershell
python run_project.py public
```

Что делает:

- поднимает backend
- поднимает Gradio с `share=True`
- печатает:
  - `Local backend docs: ...`
  - `Local demo UI: ...`
  - `Public demo UI: https://2cb0fcbccca842137d.gradio.live`

Важно:

- `public` больше не использует `ngrok`
- публичная ссылка жива, пока жив процесс
- для долгого публичного хостинга нужен отдельный deploy
- если `share=True` не смог поднять ссылку из-за сети или сервиса Gradio, это operational issue, а не дефект backend

### Только backend

```powershell
python run_project.py backend
```

### Только frontend

```powershell
python run_project.py frontend
```

По умолчанию frontend использует backend `http://127.0.0.1:8000`.

Можно указать другой backend:

```powershell
python run_project.py frontend --backend-url http://127.0.0.1:8100
```

### Отчеты и тесты

```powershell
python run_project.py report
python run_project.py test
```

## Раздельный Ручной Запуск

Backend:

```powershell
uvicorn src.avito_splitter.api:app --reload
```

Frontend:

```powershell
python demo/gradio_app.py
```

Runtime env-переменные frontend:

- `AVITO_BACKEND_URL` default `http://127.0.0.1:8000`
- `AVITO_GRADIO_SHARE` default `false`
- `AVITO_GRADIO_SERVER_NAME` default `127.0.0.1`
- `AVITO_GRADIO_SERVER_PORT` default `7860`

## Demo UI

Gradio demo поддерживает:

- `Backend URL`
- индикатор доступности backend
- dropdown `Demo-кейс`
- кнопку `Подставить кейс`
- `Item ID`
- dropdown `Микрокатегория`
- read-only preview `mcId`
- поле `Описание`
- кнопку `Обработать объявление`
- verdict по `shouldSplit`
- рендер draft-карточек
- `Raw JSON`
- сверку с эталоном demo-case

Основные demo-кейсы лежат в [demo/demo_cases.json](demo/demo_cases.json):

- комплексная услуга
- отдельные услуги
- перечисление услуг
- исключение исходной категории
- нейтральное упоминание
- смешанный контекст

## Полезные Ручные Сценарии

1. Без split:

```text
Делаем ремонт под ключ, включая электрику и сантехнику.
```

Ожидание: `shouldSplit = false`

2. Split на 2 услуги:

```text
Отдельно выполняем сантехнические и электромонтажные работы.
```

Ожидание: `shouldSplit = true`, `draftMcIds = [102, 103]`

3. Перечисление услуг:

```text
Выполняем электрику, сантехнику, натяжные потолки.
```

Ожидание: `shouldSplit = true`, `draftMcIds = [103, 102, 104]`

## Тесты

Полный прогон:

```powershell
pytest
```

Ключевые наборы:

- backend unit и regression tests
- FastAPI API tests
- Gradio smoke tests
- Playwright browser e2e на живом backend/frontend
- launcher smoke tests
- expert dataset audit regression

Отдельно:

```powershell
pytest tests/test_gradio_smoke.py
pytest tests/test_playwright_e2e.py
pytest tests/test_run_project_smoke.py
```

## Проверка Для Экспертов

Короткий маршрут:

1. Выполнить `python -m pip install -r requirements.txt`
2. Выполнить `pytest`
3. Выполнить `python run_project.py`
4. Открыть demo UI
5. Подставить demo-case `Отдельные услуги`
6. Нажать `Обработать объявление`
7. Проверить verdict, drafts и сверку с эталоном
8. При необходимости открыть `/docs`

## Операционные Замечания

- backend остается отдельным FastAPI сервисом
- frontend остается thin client поверх HTTP backend
- `share=True` подходит для demo/hackathon, но не для постоянного продакшен-хостинга
- два одновременно запущенных процесса `python run_project.py public` должны получить разные `gradio.live` ссылки, если обе share-сессии успешно поднялись
