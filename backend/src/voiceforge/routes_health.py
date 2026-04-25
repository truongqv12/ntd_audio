from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .provider_registry import list_providers
from .services_app_settings import apply_provider_settings

router = APIRouter(prefix="/health", tags=["health"])


def _alembic_revision(db: Session) -> str | None:
    try:
        return db.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
    except SQLAlchemyError:
        return None


@router.get("")
def healthcheck(db: Session = Depends(get_db)) -> dict:
    apply_provider_settings(db)
    provider_health = {}
    for provider in list_providers():
        reachable, reason = provider.healthcheck()
        provider_health[provider.key] = {
            "reachable": reachable,
            "reason": reason,
            "configured": provider.is_configured(),
        }
    return {
        "status": "ok",
        "version": settings.app_version,
        "app_env": settings.app_env,
        "alembic_revision": _alembic_revision(db),
        "providers": provider_health,
    }
