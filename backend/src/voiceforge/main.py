from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .api_router import api_router
from .config import settings
from .db import SessionLocal, init_db
from .logging_setup import setup_logging
from .services_catalog import refresh_catalog
from .services_projects import ensure_project

setup_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "http_request request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    db = SessionLocal()
    try:
        ensure_project(db)
        if settings.voice_catalog_refresh_on_start:
            refresh_catalog(db)
    finally:
        db.close()
    logger.info("startup_complete app=%s env=%s", settings.app_name, settings.app_env)


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "status": "ready"}
