from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .api_router import build_api_router
from .config import settings
from .db import SessionLocal, init_db
from .logging_setup import setup_logging
from .observability import record_http, render_metrics
from .services_catalog import refresh_catalog
from .services_jobs import reap_stale_jobs
from .services_projects import ensure_project

setup_logging()
logger = logging.getLogger(__name__)


def _refresh_catalog_safe() -> None:
    """Run catalog refresh in a fresh DB session, swallow errors."""
    db = SessionLocal()
    try:
        refresh_catalog(db)
    except Exception as exc:
        logger.warning("catalog_refresh_background_failed error=%s", exc)
    finally:
        db.close()


def _reap_stale_jobs_safe() -> None:
    db = SessionLocal()
    try:
        reap_stale_jobs(db, settings.job_max_runtime_seconds)
    except Exception as exc:
        logger.warning("stale_job_reaper_failed error=%s", exc)
    finally:
        db.close()


async def _run_periodic(coro_func, interval_seconds: int, task_name: str) -> None:
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await asyncio.to_thread(coro_func)
        except asyncio.CancelledError:
            logger.info("periodic_task_cancelled task=%s", task_name)
            raise
        except Exception as exc:
            logger.warning("periodic_task_error task=%s error=%s", task_name, exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        ensure_project(db)
    finally:
        db.close()

    background_tasks: list[asyncio.Task] = []

    if settings.voice_catalog_refresh_on_start:
        background_tasks.append(asyncio.create_task(asyncio.to_thread(_refresh_catalog_safe), name="catalog-refresh"))

    if settings.job_reaper_enabled:
        background_tasks.append(
            asyncio.create_task(
                _run_periodic(_reap_stale_jobs_safe, settings.job_reaper_interval_seconds, "reaper"),
                name="stale-job-reaper",
            )
        )

    logger.info(
        "startup_complete app=%s env=%s version=%s allowed_origins=%s",
        settings.app_name,
        settings.app_env,
        settings.app_version,
        settings.app_allowed_origins,
    )

    try:
        yield
    finally:
        for task in background_tasks:
            task.cancel()
        for task in background_tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-App-Version", "X-Request-Id"],
)

# Versioned mount is the canonical surface; the un-versioned mount stays for
# backward-compat with existing clients and is marked deprecated via a header.
app.include_router(build_api_router(), prefix="/v1")
app.include_router(build_api_router())


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    response.headers["x-app-version"] = settings.app_version
    if settings.metrics_enabled:
        route = request.scope.get("route")
        path_template = getattr(route, "path", request.url.path)
        record_http(request.method, path_template, response.status_code, elapsed_ms / 1000.0)
    logger.info(
        "http_request request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/")
def root() -> dict:
    return {"app": settings.app_name, "status": "ready", "version": settings.app_version}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    if not settings.metrics_enabled:
        return Response(status_code=404)
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
