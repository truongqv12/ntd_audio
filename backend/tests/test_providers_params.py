"""Regression coverage for `providers_params.PARAMETER_SCHEMAS`.

Pydantic 2.13 enforces stricter type checking, which surfaced a latent bug:
several `ProviderParamField` entries passed `True` as the 10th positional
argument intending to set `advanced=True`, but position 10 is `options:
list[dict[str, str]]`. Older pydantic silently accepted the bool; 2.13
rejects it and the `/v1/settings/voice-parameter-schemas` endpoint 500s.

This test serialises every entry through `ProviderParameterSchemasResponse`
so any future positional / type drift fails CI instead of production.
"""

from __future__ import annotations

from voiceforge.providers_params import get_all_parameter_schemas
from voiceforge.schemas import ProviderParameterSchemasResponse


def test_all_parameter_schemas_validate() -> None:
    schemas = get_all_parameter_schemas()
    response = ProviderParameterSchemasResponse(schemas=schemas)
    for provider_key, fields in response.schemas.items():
        for field_def in fields:
            assert isinstance(field_def.options, list), (
                f"{provider_key}.{field_def.key}.options must be a list, " f"got {type(field_def.options).__name__}"
            )
            assert isinstance(field_def.advanced, bool), f"{provider_key}.{field_def.key}.advanced must be a bool"
