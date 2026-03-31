# Avito Services Splitter Backend

Backend-only MVP для кейса выделения самостоятельных услуг и генерации черновиков без фронтенда, внешних API, БД и очередей. Первая версия использует локальный JSON-каталог микрокатегорий, нормализацию русского текста и детерминированные rules-first эвристики.

## Scope

- Реализованы backend phases 1-5 из handoff-плана.
- API принимает одно объявление и возвращает строго валидный JSON с `shouldSplit` и `drafts`.
- Swagger/OpenAPI FastAPI используется как единственный контрактный интерфейс.
- Вне scope: UI, Streamlit, внешние LLM, БД, очереди, авторизация.

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
