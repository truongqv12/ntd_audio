"""Provider registry.

Built-in providers are imported eagerly. Third-party providers are discovered
through the ``voiceforge.providers`` setuptools entry-point group: any
installed Python package may register entries shaped as ``key = pkg.module:factory``,
where ``factory`` is either a class or a callable returning a ``VoiceProvider``.

Failures during discovery are logged and skipped — one broken plugin must not
take the API down.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points

from .providers_azure_speech import AzureSpeechProvider
from .providers_base import VoiceProvider
from .providers_elevenlabs import ElevenLabsProvider
from .providers_google_tts import GoogleCloudTTSProvider
from .providers_kokoro import KokoroProvider
from .providers_openai_tts import OpenAITTSProvider
from .providers_piper import PiperProvider
from .providers_vieneu_tts import VieNeuTTSProvider
from .providers_voicevox import VoicevoxProvider

ENTRY_POINT_GROUP = "voiceforge.providers"

logger = logging.getLogger(__name__)


def _builtin_providers() -> dict[str, VoiceProvider]:
    return {
        "voicevox": VoicevoxProvider(),
        "piper": PiperProvider(),
        "kokoro": KokoroProvider(),
        "vieneu_tts": VieNeuTTSProvider(),
        "openai_tts": OpenAITTSProvider(),
        "elevenlabs": ElevenLabsProvider(),
        "google_cloud_tts": GoogleCloudTTSProvider(),
        "azure_speech": AzureSpeechProvider(),
    }


def _instantiate(target: object) -> VoiceProvider | None:
    if callable(target):
        try:
            return target()
        except Exception:  # pragma: no cover - defensive
            logger.exception("provider factory raised")
            return None
    return None


def _discover_plugins() -> dict[str, VoiceProvider]:
    discovered: dict[str, VoiceProvider] = {}
    eps = entry_points(group=ENTRY_POINT_GROUP)
    for ep in eps:
        try:
            target = ep.load()
        except Exception:
            logger.exception("failed to load provider entry point %s", ep.name)
            continue
        instance = _instantiate(target)
        if instance is None:
            logger.warning("provider entry point %s did not produce an instance", ep.name)
            continue
        discovered[ep.name] = instance
    return discovered


def _build_registry() -> dict[str, VoiceProvider]:
    registry = _builtin_providers()
    plugins = _discover_plugins()
    for key, instance in plugins.items():
        if key in registry:
            logger.warning("plugin %s shadows built-in provider; ignoring plugin", key)
            continue
        registry[key] = instance
    return registry


PROVIDERS: dict[str, VoiceProvider] = _build_registry()


def get_provider(key: str) -> VoiceProvider:
    if key not in PROVIDERS:
        raise KeyError(f"Unknown provider: {key}")
    return PROVIDERS[key]


def list_providers() -> list[VoiceProvider]:
    return list(PROVIDERS.values())


def reload_providers() -> None:
    """Re-scan entry points. Test-only — production loads at import time."""
    PROVIDERS.clear()
    PROVIDERS.update(_build_registry())
