from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .provider_registry import list_providers
from .services_app_settings import apply_provider_settings

router = APIRouter(prefix="/health", tags=["health"])


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
        "providers": provider_health,
    }
