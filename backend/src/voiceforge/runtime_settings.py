from __future__ import annotations

from threading import RLock
from typing import Any

_LOCK = RLock()
_PROVIDER_CONFIG: dict[str, dict[str, Any]] = {}


def set_provider_runtime_config(provider_key: str, config: dict[str, Any]) -> None:
    with _LOCK:
        current = dict(_PROVIDER_CONFIG.get(provider_key, {}))
        current.update({key: value for key, value in (config or {}).items() if value not in (None, "")})
        _PROVIDER_CONFIG[provider_key] = current


def get_provider_runtime_config(provider_key: str) -> dict[str, Any]:
    with _LOCK:
        return dict(_PROVIDER_CONFIG.get(provider_key, {}))


def set_all_provider_runtime_configs(configs: dict[str, dict[str, Any]]) -> None:
    with _LOCK:
        for key, value in configs.items():
            set_provider_runtime_config(key, value or {})
