# Avito Services Splitter Backend

Backend-only MVP для кейса выделения самостоятельных услуг и генерации черновиков без фронтенда, внешних API, БД и очередей. Первая версия использует локальный JSON-каталог микрокатегорий, нормализацию русского текста и детерминированные rules-first эвристики.

## Scope

- Только backend phases 1-5 из handoff-плана.
- API принимает одно объявление и возвращает строго валидный JSON с `shouldSplit` и `drafts`.
- Swagger/OpenAPI FastAPI используется как единственный контрактный интерфейс.

## Data

- `data/microcategories.raw.json` сейчас содержит seed-набор микрокатегорий из примеров ТЗ. Его нужно заменить полным словарем, когда он появится.
- `data/microcategories.enriched.json` содержит runtime-обогащение: `matchPhrases` и `draftLead`.
- `data/gold_examples.json` содержит базовые regression-кейсы для backend-пайплайна.

## Project layout

- `src/avito_splitter/` содержит доменную логику и FastAPI-обертку.
- `tests/` содержит unit, integration и API tests.
- Core-логика должна оставаться синхронной и чистой по входу/выходу; FastAPI только вызывает pipeline и сериализует ответ.

## Runbook

```bash
pip install -r requirements.txt
pytest
uvicorn src.avito_splitter.api:app --reload
```
