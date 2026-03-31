from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from .loaders import load_catalog_bundle
from .pipeline import ServicesSplitter
from .schemas import AdInput, SplitResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _, catalog = load_catalog_bundle()
    app.state.splitter = ServicesSplitter(catalog)
    yield


app = FastAPI(title="Avito Services Splitter", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/split", response_model=SplitResponse)
def split(item: AdInput, request: Request) -> SplitResponse:
    try:
        splitter: ServicesSplitter = request.app.state.splitter
        return splitter.process(item)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - exercised through API tests
        logger.exception("Unexpected splitter error", exc_info=exc)
        raise HTTPException(status_code=500, detail="Internal Server Error") from exc
