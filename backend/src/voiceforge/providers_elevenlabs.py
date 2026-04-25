import httpx

from .config import settings
from .providers_base import ProviderCapabilities, SynthesisResult, VoiceOption
from .runtime_settings import get_provider_runtime_config


class ElevenLabsProvider:
    key = "elevenlabs"
    label = "ElevenLabs"
    category = "cloud"
    capabilities = ProviderCapabilities(
        batch_generation=True,
        realtime_generation=True,
        local_inference=False,
        cloud_api=True,
        custom_voice=True,
        voice_cloning=True,
        expressive_speech=True,
        multilingual=True,
        supports_preview_audio=True,
    )

    def _cfg(self) -> dict:
        cfg = get_provider_runtime_config(self.key)
        return {
            "elevenlabs_api_key": cfg.get("elevenlabs_api_key") or settings.elevenlabs_api_key,
            "elevenlabs_model_id": cfg.get("elevenlabs_model_id") or settings.elevenlabs_model_id,
        }

    def is_configured(self) -> bool:
        return bool(self._cfg().get("elevenlabs_api_key"))

    def healthcheck(self) -> tuple[bool, str]:
        cfg = self._cfg()
        if not cfg.get("elevenlabs_api_key"):
            return False, "ELEVENLABS_API_KEY missing"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    "https://api.elevenlabs.io/v2/voices",
                    headers={"xi-api-key": cfg.get("elevenlabs_api_key")},
                )
                response.raise_for_status()
            return True, "Configured"
        except Exception as exc:
            return False, str(exc)

    def list_voices(self) -> list[VoiceOption]:
        cfg = self._cfg()
        if not cfg.get("elevenlabs_api_key"):
            return []
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                "https://api.elevenlabs.io/v2/voices",
                headers={"xi-api-key": cfg.get("elevenlabs_api_key")},
            )
            response.raise_for_status()
            payload = response.json()
        voices = []
        for item in payload.get("voices", []):
            labels = item.get("labels", {}) or {}
            voices.append(
                VoiceOption(
                    id=item["voice_id"],
                    label=item.get("name", "Unnamed Voice"),
                    language=labels.get("language"),
                    locale=labels.get("language"),
                    gender=labels.get("gender"),
                    accent=labels.get("accent"),
                    age=labels.get("age"),
                    voice_type=labels.get("descriptive"),
                    description=item.get("description"),
                    preview_url=item.get("preview_url"),
                    tags=["cloud", "elevenlabs", "cloning", "expressive"],
                    metadata={"labels": labels, "category": item.get("category")},
                )
            )
        return voices

    def synthesize(self, *, text: str, voice_id: str, output_format: str = "mp3", params: dict | None = None) -> SynthesisResult:
        cfg = self._cfg()
        if not cfg.get("elevenlabs_api_key"):
            raise RuntimeError("ELEVENLABS_API_KEY missing")
        voice_settings = {}
        for key in ("stability", "similarity_boost", "style", "speed", "use_speaker_boost"):
            if params and key in params and params[key] not in (None, ""):
                voice_settings[key] = params[key]
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                params={"output_format": "mp3_44100_128" if output_format == "mp3" else "pcm_24000"},
                headers={
                    "xi-api-key": cfg.get("elevenlabs_api_key"),
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": cfg.get("elevenlabs_model_id"),
                    "voice_settings": voice_settings,
                },
            )
            response.raise_for_status()
        return SynthesisResult(
            audio_bytes=response.content,
            mime_type="audio/mpeg" if output_format == "mp3" else "audio/wav",
            file_extension="mp3" if output_format == "mp3" else "wav",
            provider_metadata={"model_id": cfg.get("elevenlabs_model_id")},
        )
