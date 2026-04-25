from fastapi import APIRouter

from .routes_catalog import router as catalog_router
from .routes_events import router as events_router
from .routes_health import router as health_router
from .routes_jobs import router as jobs_router
from .routes_monitor import router as monitor_router
from .routes_projects import router as projects_router
from .routes_project_rows import router as project_rows_router
from .routes_settings import router as settings_router
from .routes_providers import router as providers_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(providers_router)
api_router.include_router(catalog_router)
api_router.include_router(jobs_router)
api_router.include_router(projects_router)
api_router.include_router(project_rows_router)
api_router.include_router(settings_router)
api_router.include_router(events_router)
api_router.include_router(monitor_router)
