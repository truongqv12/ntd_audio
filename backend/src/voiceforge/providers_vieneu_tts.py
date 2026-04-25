import httpx

from .config import settings
from .providers_base import ProviderCapabilities, SynthesisResult, VoiceOption
from .runtime_settings import get_provider_runtime_config


class VieNeuTTSProvider:
    key = "vieneu_tts"
    label = "VieNeu-TTS"
    category = "self_hosted"
    capabilities = ProviderCapabilities(
        batch_generation=True,
        realtime_generation=True,
        local_inference=True,
        cloud_api=False,
        custom_voice=True,
        voice_cloning=True,
        expressive_speech=True,
        multilingual=True,
        requires_gpu=False,
        supports_preview_audio=False,
    )

    def _base_url(self) -> str:
        cfg = get_provider_runtime_config(self.key)
        return str(cfg.get("vieneu_tts_base_url") or settings.vieneu_tts_base_url or "").rstrip("/")

    def _timeout(self) -> float:
        return settings.vieneu_tts_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self._base_url())

    def healthcheck(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "VIENEU_TTS_BASE_URL missing"
        try:
            with httpx.Client(timeout=self._timeout()) as client:
                response = client.get(f"{self._base_url()}/health")
                response.raise_for_status()
                payload = response.json()
            if payload.get("status") == "ok":
                return True, f"VieNeu runtime reachable ({payload.get('voices', 0)} voices)"
            return False, payload.get("detail", "VieNeu runtime unhealthy")
        except Exception as exc:
            return False, str(exc)

    def list_voices(self) -> list[VoiceOption]:
        if not self.is_configured():
            return []
        with httpx.Client(timeout=self._timeout()) as client:
            response = client.get(f"{self._base_url()}/voices")
            response.raise_for_status()
            payload = response.json()
        rows = payload.get("voices", payload)
        return [
            VoiceOption(
                id=str(row["id"]),
                label=row.get("label", row["id"]),
                language=row.get("language"),
                locale=row.get("locale"),
                gender=row.get("gender"),
                voice_type=row.get("voice_type", "narration"),
                description=row.get("description"),
                accent=row.get("accent"),
                age=row.get("age"),
                styles=list(row.get("styles", [])),
                tags=list(row.get("tags", [])) or ["vieneu"],
                preview_url=row.get("preview_url"),
                metadata=row.get("metadata", {}),
            )
            for row in rows
        ]

    def synthesize(
        self, *, text: str, voice_id: str, output_format: str = "wav", params: dict | None = None
    ) -> SynthesisResult:
        if not self.is_configured():
            raise RuntimeError("VIENEU_TTS_BASE_URL missing")
        with httpx.Client(timeout=max(self._timeout(), 240.0)) as client:
            response = client.post(
                f"{self._base_url()}/synthesize",
                json={
                    "text": text,
                    "voice": voice_id,
                    "format": output_format,
                    "reference_audio_path": (params or {}).get("reference_audio_path"),
                    "reference_text": (params or {}).get("reference_text"),
                    "speed": (params or {}).get("speed"),
                },
            )
            response.raise_for_status()
        extension = response.headers.get("x-audio-extension", output_format)
        mime = "audio/wav" if extension == "wav" else "audio/mpeg"
        return SynthesisResult(
            audio_bytes=response.content,
            mime_type=mime,
            file_extension=extension,
            provider_metadata={"engine": "vieneu_tts", "voice_id": voice_id},
        )
