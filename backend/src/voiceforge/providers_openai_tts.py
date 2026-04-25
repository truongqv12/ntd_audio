import httpx

from .config import settings
from .providers_base import ProviderCapabilities, SynthesisResult, VoiceOption
from .runtime_settings import get_provider_runtime_config

OPENAI_VOICES = [
    ("alloy", "Alloy"),
    ("ash", "Ash"),
    ("ballad", "Ballad"),
    ("coral", "Coral"),
    ("echo", "Echo"),
    ("fable", "Fable"),
    ("nova", "Nova"),
    ("onyx", "Onyx"),
    ("sage", "Sage"),
    ("shimmer", "Shimmer"),
    ("verse", "Verse"),
    ("marin", "Marin"),
    ("cedar", "Cedar"),
]


class OpenAITTSProvider:
    key = "openai_tts"
    label = "OpenAI TTS"
    category = "cloud"
    capabilities = ProviderCapabilities(
        batch_generation=True,
        realtime_generation=True,
        local_inference=False,
        cloud_api=True,
        expressive_speech=True,
        multilingual=True,
        supports_preview_audio=False,
    )

    def _cfg(self) -> dict:
        cfg = get_provider_runtime_config(self.key)
        return {
            "openai_api_key": cfg.get("openai_api_key") or settings.openai_api_key,
            "openai_tts_model": cfg.get("openai_tts_model") or settings.openai_tts_model,
        }

    def is_configured(self) -> bool:
        return bool(self._cfg().get("openai_api_key"))

    def healthcheck(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "OPENAI_API_KEY missing"
        return True, "Configured"

    def list_voices(self) -> list[VoiceOption]:
        return [
            VoiceOption(
                id=voice_id,
                label=label,
                language="Primarily English",
                locale="multi",
                voice_type="narration",
                description="Built-in OpenAI TTS voice.",
                tags=["cloud", "openai", "expressive"],
            )
            for voice_id, label in OPENAI_VOICES
        ]

    def synthesize(self, *, text: str, voice_id: str, output_format: str = "mp3", params: dict | None = None) -> SynthesisResult:
        cfg = self._cfg()
        if not cfg.get("openai_api_key"):
            raise RuntimeError("OPENAI_API_KEY missing")
        payload = {
            "model": cfg.get("openai_tts_model"),
            "voice": voice_id,
            "input": text,
            "response_format": output_format,
        }
        if params and params.get("instructions"):
            payload["instructions"] = params["instructions"]
        if params and params.get("speed") not in (None, ""):
            payload["speed"] = float(params["speed"])
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {cfg.get('openai_api_key')}"},
                json=payload,
            )
            response.raise_for_status()
        mime = "audio/mpeg" if output_format == "mp3" else f"audio/{output_format}"
        return SynthesisResult(
            audio_bytes=response.content,
            mime_type=mime,
            file_extension=output_format,
            provider_metadata={"model": cfg.get("openai_tts_model")},
        )
