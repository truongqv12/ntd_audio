from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import AppSetting
from .provider_registry import list_providers
from .providers_params import get_all_parameter_schemas
from .runtime_settings import set_all_provider_runtime_configs
from .schemas import ProviderCredentialResponse, SettingsOverviewResponse
from .security.encryption import decrypt_value, encrypt_value

PROVIDER_CREDENTIAL_FIELDS: dict[str, dict[str, dict[str, Any]]] = {
    "openai_tts": {
        "openai_api_key": {"label": "OpenAI API key", "secret": True, "env": "OPENAI_API_KEY"},
        "openai_tts_model": {"label": "TTS model", "secret": False, "env": "OPENAI_TTS_MODEL"},
    },
    "elevenlabs": {
        "elevenlabs_api_key": {"label": "ElevenLabs API key", "secret": True, "env": "ELEVENLABS_API_KEY"},
        "elevenlabs_model_id": {"label": "Model ID", "secret": False, "env": "ELEVENLABS_MODEL_ID"},
    },
    "google_cloud_tts": {
        "google_tts_access_token": {"label": "Google access token", "secret": True, "env": "GOOGLE_TTS_ACCESS_TOKEN"},
        "google_tts_project_id": {"label": "Project ID", "secret": False, "env": "GOOGLE_TTS_PROJECT_ID"},
    },
    "azure_speech": {
        "azure_speech_key": {"label": "Azure Speech key", "secret": True, "env": "AZURE_SPEECH_KEY"},
        "azure_speech_region": {"label": "Azure region", "secret": False, "env": "AZURE_SPEECH_REGION"},
    },
    "voicevox": {
        "voicevox_base_url": {"label": "VOICEVOX base URL", "secret": False, "env": "VOICEVOX_BASE_URL"},
    },
    "piper": {
        "piper_base_url": {"label": "Piper runtime URL", "secret": False, "env": "PIPER_BASE_URL"},
    },
    "kokoro": {
        "kokoro_base_url": {"label": "Kokoro runtime URL", "secret": False, "env": "KOKORO_BASE_URL"},
    },
    "vieneu_tts": {
        "vieneu_tts_base_url": {"label": "VieNeu runtime URL", "secret": False, "env": "VIENEU_TTS_BASE_URL"},
    },
}

DEFAULT_MERGE_SETTINGS = {
    "merge_silence_ms": 150,
    "merge_output_format": "wav",
    "normalize_loudness": False,
    "crossfade_ms": 0,
}


def _secret_field_names(namespace: str, key: str) -> set[str]:
    if namespace != "provider_credentials":
        return set()
    fields = PROVIDER_CREDENTIAL_FIELDS.get(key, {})
    return {name for name, meta in fields.items() if meta.get("secret")}


def _decrypt_stored(value: dict[str, Any], secret_fields: set[str]) -> dict[str, Any]:
    if not value or not secret_fields:
        return value
    return {k: (decrypt_value(v) if k in secret_fields else v) for k, v in value.items()}


def _encrypt_for_storage(value: dict[str, Any], secret_fields: set[str]) -> dict[str, Any]:
    if not value or not secret_fields:
        return value
    return {k: (encrypt_value(v) if k in secret_fields and isinstance(v, str) else v) for k, v in value.items()}


def _get_setting(db: Session, namespace: str, key: str) -> dict[str, Any]:
    row = db.scalar(select(AppSetting).where(AppSetting.namespace == namespace, AppSetting.key == key))
    if not row:
        return {}
    raw = dict(row.value_json or {})
    return _decrypt_stored(raw, _secret_field_names(namespace, key))


def _upsert_setting(
    db: Session, namespace: str, key: str, value: dict[str, Any], *, is_secret: bool = False
) -> AppSetting:
    payload = _encrypt_for_storage(value, _secret_field_names(namespace, key))
    row = db.scalar(select(AppSetting).where(AppSetting.namespace == namespace, AppSetting.key == key))
    if row is None:
        row = AppSetting(namespace=namespace, key=key, value_json=payload, is_secret=is_secret)
        db.add(row)
    else:
        row.value_json = payload
        row.is_secret = is_secret
        row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def _env_value(field: str) -> Any:
    return getattr(settings, field, "")


def _mask(value: Any) -> Any:
    if value in (None, ""):
        return ""
    raw = str(value)
    if len(raw) <= 8:
        return "••••"
    return f"{raw[:3]}••••{raw[-3:]}"


def provider_effective_config(db: Session, provider_key: str) -> dict[str, Any]:
    stored = _get_setting(db, "provider_credentials", provider_key)
    fields = PROVIDER_CREDENTIAL_FIELDS.get(provider_key, {})
    merged: dict[str, Any] = {}
    for field in fields:
        env = _env_value(field)
        if env not in (None, ""):
            merged[field] = env
        elif stored.get(field) not in (None, ""):
            merged[field] = stored[field]
    return merged


def apply_provider_settings(db: Session) -> None:
    configs = {provider.key: provider_effective_config(db, provider.key) for provider in list_providers()}
    set_all_provider_runtime_configs(configs)


def list_provider_credentials(db: Session) -> list[ProviderCredentialResponse]:
    providers = {provider.key: provider for provider in list_providers()}
    items: list[ProviderCredentialResponse] = []
    for provider_key, fields in PROVIDER_CREDENTIAL_FIELDS.items():
        provider = providers.get(provider_key)
        stored = _get_setting(db, "provider_credentials", provider_key)
        effective = provider_effective_config(db, provider_key)
        response_fields = {}
        effective_fields = {}
        env_overrides: list[str] = []
        configured = False
        for field, meta in fields.items():
            secret = bool(meta.get("secret"))
            env_present = _env_value(field) not in (None, "")
            if env_present:
                env_overrides.append(field)
            raw = stored.get(field, "")
            eff = effective.get(field, "")
            configured = configured or bool(eff)
            response_fields[field] = {
                "label": meta.get("label", field),
                "secret": secret,
                "value": _mask(raw) if secret else raw,
                "env": meta.get("env"),
                "env_present": env_present,
            }
            effective_fields[field] = _mask(eff) if secret else eff
        items.append(
            ProviderCredentialResponse(
                provider_key=provider_key,
                label=provider.label if provider else provider_key,
                category=provider.category if provider else "unknown",
                fields=response_fields,
                effective_fields=effective_fields,
                configured=configured,
                env_overrides=env_overrides,
            )
        )
    return items


def update_provider_credentials(db: Session, provider_key: str, fields: dict[str, Any]) -> ProviderCredentialResponse:
    allowed = PROVIDER_CREDENTIAL_FIELDS.get(provider_key)
    if allowed is None:
        raise KeyError(f"Unknown provider settings: {provider_key}")
    current = _get_setting(db, "provider_credentials", provider_key)
    for key, value in fields.items():
        if key not in allowed:
            continue
        # Masked values mean the user did not change the secret in the UI.
        if isinstance(value, str) and "••••" in value:
            continue
        current[key] = value
    is_secret = any(bool(item.get("secret")) for item in allowed.values())
    _upsert_setting(db, "provider_credentials", provider_key, current, is_secret=is_secret)
    apply_provider_settings(db)
    return next(item for item in list_provider_credentials(db) if item.provider_key == provider_key)


def get_merge_defaults(db: Session) -> dict[str, Any]:
    stored = _get_setting(db, "merge_defaults", "global")
    return {**DEFAULT_MERGE_SETTINGS, **stored}


def update_merge_defaults(db: Session, fields: dict[str, Any]) -> dict[str, Any]:
    current = get_merge_defaults(db)
    for key in DEFAULT_MERGE_SETTINGS:
        if key in fields:
            current[key] = fields[key]
    _upsert_setting(db, "merge_defaults", "global", current)
    return current


def settings_overview(db: Session) -> SettingsOverviewResponse:
    apply_provider_settings(db)
    return SettingsOverviewResponse(
        provider_credentials=list_provider_credentials(db),
        voice_parameter_schemas=get_all_parameter_schemas(),
        merge_defaults=get_merge_defaults(db),
    )
