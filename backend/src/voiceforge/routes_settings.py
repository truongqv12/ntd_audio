from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .providers_params import get_all_parameter_schemas, get_parameter_schema
from .schemas import (
    ProviderCredentialResponse,
    ProviderCredentialUpdateRequest,
    ProviderParameterSchemasResponse,
    SettingsOverviewResponse,
)
from .services_app_settings import (
    list_provider_credentials,
    settings_overview,
    update_merge_defaults,
    update_provider_credentials,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOverviewResponse)
def get_settings(db: Session = Depends(get_db)) -> SettingsOverviewResponse:
    return settings_overview(db)


@router.get("/provider-credentials", response_model=list[ProviderCredentialResponse])
def get_provider_credentials(db: Session = Depends(get_db)) -> list[ProviderCredentialResponse]:
    return list_provider_credentials(db)


@router.put("/provider-credentials/{provider_key}", response_model=ProviderCredentialResponse)
def put_provider_credentials(
    provider_key: str, payload: ProviderCredentialUpdateRequest, db: Session = Depends(get_db)
) -> ProviderCredentialResponse:
    try:
        return update_provider_credentials(db, provider_key, payload.fields)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/voice-parameter-schemas", response_model=ProviderParameterSchemasResponse)
def get_voice_parameter_schemas() -> ProviderParameterSchemasResponse:
    return ProviderParameterSchemasResponse(schemas=get_all_parameter_schemas())


@router.get("/voice-parameter-schemas/{provider_key}")
def get_voice_parameter_schema(provider_key: str) -> dict:
    return {"provider_key": provider_key, "fields": get_parameter_schema(provider_key)}


@router.patch("/merge-defaults")
def patch_merge_defaults(payload: dict, db: Session = Depends(get_db)) -> dict:
    return update_merge_defaults(db, payload)
