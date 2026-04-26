from fastapi import APIRouter, Depends

from .rate_limit import check_rate_limit
from .routes_catalog import router as catalog_router
from .routes_events import router as events_router
from .routes_health import router as health_router
from .routes_jobs import router as jobs_router
from .routes_monitor import router as monitor_router
from .routes_project_rows import router as project_rows_router
from .routes_projects import router as projects_router
from .routes_providers import router as providers_router
from .routes_settings import router as settings_router
from .security.api_key import require_api_key


def _build_api_router() -> APIRouter:
    """Compose the API surface.

    `/health` is intentionally public — Docker / k8s healthchecks must reach
    it unauthenticated. Everything else is gated behind APP_API_KEYS (no-op
    when empty) and the rate limiter (no-op when RATE_LIMIT_PER_MINUTE=0).
    """
    router = APIRouter()
    router.include_router(health_router)

    protected = [Depends(require_api_key), Depends(check_rate_limit)]
    router.include_router(providers_router, dependencies=protected)
    router.include_router(catalog_router, dependencies=protected)
    router.include_router(jobs_router, dependencies=protected)
    router.include_router(projects_router, dependencies=protected)
    router.include_router(project_rows_router, dependencies=protected)
    router.include_router(settings_router, dependencies=protected)
    router.include_router(events_router, dependencies=protected)
    router.include_router(monitor_router, dependencies=protected)
    return router


# Each call returns a fresh router so the un-versioned (legacy) and `/v1`
# mounts in main.py are independent FastAPI sub-routers.
def build_api_router() -> APIRouter:
    return _build_api_router()


# Backward-compatible alias for callers that imported the module-level router.
api_router = _build_api_router()
