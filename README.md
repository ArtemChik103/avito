# Avito Services Splitter

MVP для кейса выделения самостоятельных услуг и генерации черновиков. Проект состоит из локального backend-сервиса на FastAPI и demo frontend на Streamlit. Основная логика использует локальный JSON-каталог микрокатегорий, нормализацию русского текста и детерминированные rules-first эвристики.

## Scope

- Реализованы backend phases 1-5 и demo frontend phase 6.
- API принимает одно объявление и возвращает строго валидный JSON с `shouldSplit` и `drafts`.
- Swagger/OpenAPI FastAPI используется как единственный контрактный интерфейс.
- Вне scope: внешние LLM, БД, очереди, авторизация.

## Requirements

- Базовый таргет: Python 3.10+.
- Зависимости перечислены в `requirements.txt`.

## Data

- `data/microcategories.raw.json` сейчас содержит seed-набор микрокатегорий из примеров ТЗ. Его нужно заменить полным словарем, когда он появится.
- `data/microcategories.enriched.json` содержит runtime-обогащение: `matchPhrases` и `draftLead`.
- `data/gold_examples.json` содержит базовые regression-кейсы для backend-пайплайна.

## Project layout

- `src/avito_splitter/` содержит доменную логику и FastAPI-обертку.
- `tests/` содержит unit, integration и API tests.
- Core-логика остается синхронной и чистой по входу/выходу; FastAPI только вызывает pipeline и сериализует ответ.

## Runbook

```bash
pip install -r requirements.txt
pytest
uvicorn src.avito_splitter.api:app --reload
```

Самый простой запуск всего проекта:

```bash
python run_project.py
```

Это поднимет backend и Streamlit вместе. После старта открой:

- `http://127.0.0.1:8501` — demo UI
- `http://127.0.0.1:8000/docs` — FastAPI docs

Самые полезные команды:

```bash
python run_project.py
python run_project.py report
python run_project.py test
python run_project.py backend
python run_project.py frontend
```

Для пересчета метрик на расширенном synthetic-наборе:

```bash
python -c "from pathlib import Path; from src.avito_splitter.evaluation import evaluate_file; print(evaluate_file(Path('data/synthetic_eval_examples.json')))"
```

Для полного табличного отчета по всем case-файлам:

```bash
python run_project.py report
```

После старта сервера доступны:

- `GET /health`
- `POST /split`
- `/docs`

Пример запроса:

```json
{
  "itemId": 5002,
  "mcId": 201,
  "mcTitle": "Ремонт квартир и домов под ключ",
  "description": "Делаем ремонт квартир под ключ, а также отдельно выполняем сантехнические и электромонтажные работы."
}
```

## Acceptance Notes

- Один `mcId` порождает не более одного draft.
- Исходный `item.mcId` исключается на этапе extraction и не попадает в `drafts`.
- `drafts` всегда список, даже если он пустой.
- Порядок `drafts` детерминирован и привязан к первому подтвержденному появлению услуги.
- Bare mention без подтверждающего контекста не создает черновик.
- Если для микрокатегории есть и `blocked`, и `confirmed` evidence в разных фрагментах, приоритет у `confirmed`.
- Каталог загружается на startup приложения; ошибка данных роняет сервис при старте.
- Решение работает локально и не зависит от внешних API.

## Test coverage

- `pytest` покрывает preprocessing, extractor, independence analyzer, draft generator, pipeline и FastAPI API.
- Закрыты обязательные регрессии: blocking-context, separate services, перечисление, исключение исходной категории, neutral-only mention, соседний clause и дедупликация черновиков.
- Дополнительный synthetic evaluation dataset в `data/synthetic_eval_examples.json` расширяет покрытие до 25 размеченных кейсов для локального пересчета метрик.

## Demo Frontend

В рамках фазы 6 добавлен Streamlit demo-интерфейс, который работает локально и обращается к backend-сервису по HTTP.

### Запуск Demo

1. Самый короткий вариант:
   ```bash
   python run_project.py
   ```
2. Если нужен ручной раздельный запуск:
   ```bash
   pip install -r requirements.txt
   uvicorn src.avito_splitter.api:app --reload
   streamlit run demo/streamlit_app.py
   ```

### Demo Troubleshooting
- **Backend не отвечает:** Убедитесь, что `uvicorn` запущен на порту `8000`.
- **Порт 8000 занят:** Запустите uvicorn на другом порту (`--port 8001`) и поменяйте `Backend URL` в боковой панели Streamlit.
- **Streamlit не видит обновления:** Убедитесь, что вы обновили страницу браузера или нажали "R" в Streamlit для rerun.
- **Не установлен streamlit:** Убедитесь, что выполнили `pip install -r requirements.txt`.

*Примечание: скрипты synthetic evaluation (`data/synthetic_eval_examples.json`) остаются чисто backend-инструментом. В UI вынесены только наглядные demo-кейсы (`demo/demo_cases.json`).*
