import httpx

from .config import settings
from .providers_base import ProviderCapabilities, SynthesisResult, VoiceOption
from .runtime_settings import get_provider_runtime_config


class KokoroProvider:
    key = "kokoro"
    label = "Kokoro"
    category = "self_hosted"
    capabilities = ProviderCapabilities(
        batch_generation=True,
        realtime_generation=True,
        local_inference=True,
        cloud_api=False,
        expressive_speech=True,
        multilingual=True,
        requires_gpu=False,
        supports_preview_audio=False,
    )

    def _base_url(self) -> str:
        cfg = get_provider_runtime_config(self.key)
        return str(cfg.get("kokoro_base_url") or settings.kokoro_base_url or "").rstrip("/")

    def _timeout(self) -> float:
        return settings.kokoro_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self._base_url())

    def healthcheck(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "KOKORO_BASE_URL missing"
        try:
            with httpx.Client(timeout=self._timeout()) as client:
                response = client.get(f"{self._base_url()}/health")
                response.raise_for_status()
                payload = response.json()
            if payload.get("status") == "ok":
                return True, f"Kokoro runtime reachable ({payload.get('voices', 0)} voices)"
            return False, payload.get("detail", "Kokoro runtime unhealthy")
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
                tags=list(row.get("tags", [])) or ["kokoro"],
                preview_url=row.get("preview_url"),
                metadata=row.get("metadata", {}),
            )
            for row in rows
        ]

    def synthesize(
        self, *, text: str, voice_id: str, output_format: str = "wav", params: dict | None = None
    ) -> SynthesisResult:
        if not self.is_configured():
            raise RuntimeError("KOKORO_BASE_URL missing")
        with httpx.Client(timeout=max(self._timeout(), 180.0)) as client:
            response = client.post(
                f"{self._base_url()}/synthesize",
                json={
                    "text": text,
                    "voice": voice_id,
                    "format": output_format,
                    "speed": (params or {}).get("speed") or 1.0,
                },
            )
            response.raise_for_status()
        extension = response.headers.get("x-audio-extension", output_format)
        mime = "audio/wav" if extension == "wav" else "audio/mpeg"
        return SynthesisResult(
            audio_bytes=response.content,
            mime_type=mime,
            file_extension=extension,
            provider_metadata={"engine": "kokoro", "voice_id": voice_id},
        )
