from fastapi import APIRouter, Depends

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

# /health is intentionally public — Docker/k8s healthchecks must reach it
# unauthenticated.
api_router = APIRouter()
api_router.include_router(health_router)

# Everything else is gated behind APP_API_KEYS (no-op when the env var is empty).
protected = [Depends(require_api_key)]
api_router.include_router(providers_router, dependencies=protected)
api_router.include_router(catalog_router, dependencies=protected)
api_router.include_router(jobs_router, dependencies=protected)
api_router.include_router(projects_router, dependencies=protected)
api_router.include_router(project_rows_router, dependencies=protected)
api_router.include_router(settings_router, dependencies=protected)
api_router.include_router(events_router, dependencies=protected)
api_router.include_router(monitor_router, dependencies=protected)
