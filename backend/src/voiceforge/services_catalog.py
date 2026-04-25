from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from urllib.parse import quote

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from .config import settings
from .models import VoiceCatalogEntry
from .services_app_settings import apply_provider_settings
from .provider_registry import list_providers
from .schemas import (
    CatalogResponse,
    ProviderCapabilitiesResponse,
    ProviderSummaryResponse,
    VoiceCatalogEntryResponse,
    VoiceSearchResponse,
)

logger = logging.getLogger(__name__)


def _list_voices_with_timeout(provider, timeout_seconds: float):
    """Call provider.list_voices() with a per-provider timeout. Returns [] on timeout/error."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(provider.list_voices)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            logger.warning("provider_list_voices_timeout provider=%s timeout=%s", provider.key, timeout_seconds)
            return []
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider_list_voices_error provider=%s error=%s", provider.key, exc)
            return []


def _provider_summary(provider) -> ProviderSummaryResponse:
    reachable, reason = provider.healthcheck()
    return ProviderSummaryResponse(
        key=provider.key,
        label=provider.label,
        category=provider.category,
        configured=provider.is_configured(),
        reachable=reachable,
        reason=reason,
        capabilities=ProviderCapabilitiesResponse(**provider.capabilities.to_dict()),
    )


def _serialize_voice(row: VoiceCatalogEntry) -> VoiceCatalogEntryResponse:
    preview_url = row.preview_url
    if not preview_url and row.provider_category == "self_hosted":
        preview_url = f"/providers/{row.provider_key}/voices/{quote(str(row.provider_voice_id), safe='')}/preview"
    return VoiceCatalogEntryResponse(
        provider_key=row.provider_key,
        provider_label=row.provider_label,
        provider_category=row.provider_category,
        provider_voice_id=row.provider_voice_id,
        display_name=row.display_name,
        locale=row.locale,
        language=row.language,
        gender=row.gender,
        voice_type=row.voice_type,
        description=row.description,
        accent=row.accent,
        age=row.age,
        styles=list(row.styles or []),
        tags=list(row.tags or []),
        preview_url=preview_url,
        capabilities=ProviderCapabilitiesResponse(**row.capabilities),
        provider_metadata=row.provider_metadata or {},
    )


def refresh_catalog(db: Session) -> CatalogResponse:
    apply_provider_settings(db)
    providers = list_providers()
    existing_rows = db.scalars(select(VoiceCatalogEntry)).all()
    existing_map = {(row.provider_key, row.provider_voice_id): row for row in existing_rows}
    seen_keys: set[tuple[str, str]] = set()

    timeout_seconds = settings.voice_catalog_refresh_timeout_seconds
    for provider in providers:
        summary = _provider_summary(provider)
        if not summary.configured:
            continue
        voices = _list_voices_with_timeout(provider, timeout_seconds)
        for voice in voices:
            key = (provider.key, voice.id)
            seen_keys.add(key)
            row = existing_map.get(key)
            if row is None:
                row = VoiceCatalogEntry(
                    provider_key=provider.key,
                    provider_label=provider.label,
                    provider_category=provider.category,
                    provider_voice_id=voice.id,
                )
                db.add(row)
            row.provider_label = provider.label
            row.provider_category = provider.category
            row.display_name = voice.label
            row.locale = voice.locale
            row.language = voice.language
            row.gender = voice.gender
            row.voice_type = voice.voice_type
            row.description = voice.description
            row.accent = voice.accent
            row.age = voice.age
            row.styles = voice.styles
            row.tags = voice.tags
            row.preview_url = voice.preview_url or (f"/providers/{provider.key}/voices/{quote(str(voice.id), safe='')}/preview" if provider.category == "self_hosted" else None)
            row.capabilities = provider.capabilities.to_dict()
            row.provider_metadata = voice.metadata
            row.is_active = True
            row.last_synced_at = datetime.utcnow()

    for row in existing_rows:
        if (row.provider_key, row.provider_voice_id) not in seen_keys:
            row.is_active = False

    db.commit()
    return read_catalog(db)


def read_catalog(db: Session) -> CatalogResponse:
    apply_provider_settings(db)
    rows = db.scalars(
        select(VoiceCatalogEntry)
        .where(VoiceCatalogEntry.is_active.is_(True))
        .order_by(VoiceCatalogEntry.provider_label, VoiceCatalogEntry.display_name)
    ).all()
    providers = [_provider_summary(provider) for provider in list_providers()]
    voices = [_serialize_voice(row) for row in rows]
    if not voices:
        return refresh_catalog(db)
    return CatalogResponse(
        refreshed_at=max((row.last_synced_at for row in rows), default=datetime.utcnow()),
        providers=providers,
        voices=voices,
        filters=_build_filters(voices),
    )


def search_catalog(
    db: Session,
    *,
    q: str = "",
    provider_key: str | None = None,
    language: str | None = None,
    locale: str | None = None,
    voice_type: str | None = None,
    limit: int = 60,
) -> VoiceSearchResponse:
    stmt = select(VoiceCatalogEntry).where(VoiceCatalogEntry.is_active.is_(True))
    if provider_key:
        stmt = stmt.where(VoiceCatalogEntry.provider_key == provider_key)
    if language:
        stmt = stmt.where(VoiceCatalogEntry.language == language)
    if locale:
        stmt = stmt.where(VoiceCatalogEntry.locale == locale)
    if voice_type:
        stmt = stmt.where(VoiceCatalogEntry.voice_type == voice_type)

    normalized_q = q.strip()
    if normalized_q:
        like = f"%{normalized_q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(VoiceCatalogEntry.display_name).like(like),
                func.lower(func.coalesce(VoiceCatalogEntry.description, "")).like(like),
                func.lower(func.coalesce(VoiceCatalogEntry.language, "")).like(like),
                func.lower(func.coalesce(VoiceCatalogEntry.locale, "")).like(like),
                func.lower(func.coalesce(VoiceCatalogEntry.provider_label, "")).like(like),
                func.lower(cast(VoiceCatalogEntry.tags, String)).like(like),
                func.lower(cast(VoiceCatalogEntry.styles, String)).like(like),
            )
        )

    rows = db.scalars(
        stmt.order_by(VoiceCatalogEntry.provider_label, VoiceCatalogEntry.display_name).limit(max(1, min(limit, 200)))
    ).all()
    return VoiceSearchResponse(items=[_serialize_voice(row) for row in rows], total=len(rows), query=normalized_q)


def _build_filters(voices: list[VoiceCatalogEntryResponse]) -> dict:
    return {
        "providers": sorted({item.provider_key for item in voices}),
        "languages": sorted({item.language for item in voices if item.language}),
        "voice_types": sorted({item.voice_type for item in voices if item.voice_type}),
        "tags": sorted({tag for item in voices for tag in item.tags}),
    }
