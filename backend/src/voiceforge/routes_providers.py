from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .provider_registry import get_provider, list_providers
from .schemas import ProviderCapabilitiesResponse, ProviderSummaryResponse, VoiceCatalogEntryResponse
from .services_app_settings import apply_provider_settings

router = APIRouter(prefix="/providers", tags=["providers"])


def _preview_text_for_voice(voice: VoiceCatalogEntryResponse) -> str:
    locale = (voice.locale or "").lower()
    language = (voice.language or "").lower()
    if locale.startswith("vi") or "vietnam" in language:
        return settings.preview_sample_text_vi
    return settings.preview_sample_text_en


def _serialize_voice(provider, voice) -> VoiceCatalogEntryResponse:
    preview_url = voice.preview_url
    if not preview_url and provider.category == "self_hosted":
        preview_url = f"/providers/{provider.key}/voices/{quote(str(voice.id), safe='')}/preview"
    return VoiceCatalogEntryResponse(
        provider_key=provider.key,
        provider_label=provider.label,
        provider_category=provider.category,
        provider_voice_id=voice.id,
        display_name=voice.label,
        locale=voice.locale,
        language=voice.language,
        gender=voice.gender,
        voice_type=voice.voice_type,
        description=voice.description,
        accent=voice.accent,
        age=voice.age,
        styles=voice.styles,
        tags=voice.tags,
        preview_url=preview_url,
        capabilities=ProviderCapabilitiesResponse(**provider.capabilities.to_dict()),
        provider_metadata=voice.metadata,
    )


@router.get("", response_model=list[ProviderSummaryResponse])
def get_providers(db: Session = Depends(get_db)) -> list[ProviderSummaryResponse]:
    apply_provider_settings(db)
    items = []
    for provider in list_providers():
        reachable, reason = provider.healthcheck()
        items.append(
            ProviderSummaryResponse(
                key=provider.key,
                label=provider.label,
                category=provider.category,
                configured=provider.is_configured(),
                reachable=reachable,
                reason=reason,
                capabilities=ProviderCapabilitiesResponse(**provider.capabilities.to_dict()),
            )
        )
    return items


@router.get("/{provider_key}/voices", response_model=list[VoiceCatalogEntryResponse])
def get_provider_voices(provider_key: str, db: Session = Depends(get_db)) -> list[VoiceCatalogEntryResponse]:
    apply_provider_settings(db)
    provider = next((item for item in list_providers() if item.key == provider_key), None)
    if not provider:
        return []
    return [_serialize_voice(provider, voice) for voice in provider.list_voices()]


def _enforce_preview_length(text: str) -> str:
    cap = settings.preview_max_chars
    if len(text) > cap:
        raise HTTPException(status_code=413, detail=f"Preview text exceeds limit ({len(text)} > {cap} chars)")
    return text


@router.get("/{provider_key}/voices/{voice_id:path}/preview")
def preview_provider_voice(
    provider_key: str, voice_id: str, text: str | None = Query(default=None), db: Session = Depends(get_db)
):
    apply_provider_settings(db)
    try:
        provider = get_provider(provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    voices = provider.list_voices()
    voice = next((item for item in voices if str(item.id) == voice_id), None)
    if voice is None:
        raise HTTPException(status_code=404, detail=f"Voice not found: {voice_id}")

    serialized = _serialize_voice(provider, voice)
    sample_text = _enforce_preview_length(text or _preview_text_for_voice(serialized))
    try:
        result = provider.synthesize(text=sample_text, voice_id=voice_id, output_format="wav", params={})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(content=result.audio_bytes, media_type=result.mime_type)


class PreviewSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice_id: str = Field(..., min_length=1)
    output_format: str = "wav"
    params: dict = Field(default_factory=dict)


@router.post("/{provider_key}/preview")
def preview_arbitrary_text(
    provider_key: str,
    payload: PreviewSynthesisRequest,
    db: Session = Depends(get_db),
):
    """Synthesize on demand without persisting a job or artifact (T1.4).

    Use case: previewing a single script row before queueing a batch.
    The audio bytes are returned directly; nothing is written to disk
    or the database.
    """
    apply_provider_settings(db)
    try:
        provider = get_provider(provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    text = _enforce_preview_length(payload.text)
    try:
        result = provider.synthesize(
            text=text,
            voice_id=payload.voice_id,
            output_format=payload.output_format,
            params=payload.params,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return Response(content=result.audio_bytes, media_type=result.mime_type)
