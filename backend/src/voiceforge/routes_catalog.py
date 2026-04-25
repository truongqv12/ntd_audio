from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import CatalogResponse, VoiceSearchResponse
from .services_catalog import read_catalog, refresh_catalog, search_catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/voices", response_model=CatalogResponse)
def get_catalog(
    refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> CatalogResponse:
    return refresh_catalog(db) if refresh else read_catalog(db)


@router.get("/voices/search", response_model=VoiceSearchResponse)
def search_catalog_route(
    q: str = Query(default=""),
    provider_key: str | None = Query(default=None),
    language: str | None = Query(default=None),
    locale: str | None = Query(default=None),
    voice_type: str | None = Query(default=None),
    limit: int = Query(default=60, ge=1, le=200),
    db: Session = Depends(get_db),
) -> VoiceSearchResponse:
    return search_catalog(
        db,
        q=q,
        provider_key=provider_key,
        language=language,
        locale=locale,
        voice_type=voice_type,
        limit=limit,
    )
