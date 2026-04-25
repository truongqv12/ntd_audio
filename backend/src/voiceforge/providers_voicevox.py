import httpx

from .config import settings
from .providers_base import ProviderCapabilities, SynthesisResult, VoiceOption
from .runtime_settings import get_provider_runtime_config


class VoicevoxProvider:
    key = "voicevox"
    label = "VOICEVOX"
    category = "self_hosted"
    capabilities = ProviderCapabilities(
        batch_generation=True,
        realtime_generation=False,
        local_inference=True,
        cloud_api=False,
        expressive_speech=True,
        multilingual=False,
        requires_gpu=False,
        supports_preview_audio=False,
    )

    def _base_url(self) -> str:
        cfg = get_provider_runtime_config(self.key)
        return str(cfg.get("voicevox_base_url") or settings.voicevox_base_url).rstrip("/")

    def is_configured(self) -> bool:
        return bool(self._base_url())

    def healthcheck(self) -> tuple[bool, str]:
        try:
            with httpx.Client(timeout=settings.voicevox_timeout_seconds) as client:
                response = client.get(f"{self._base_url()}/version")
                response.raise_for_status()
            return True, "VOICEVOX engine reachable"
        except Exception as exc:
            return False, str(exc)

    def list_voices(self) -> list[VoiceOption]:
        if not self.is_configured():
            return []
        with httpx.Client(timeout=settings.voicevox_timeout_seconds) as client:
            response = client.get(f"{self._base_url()}/speakers")
            response.raise_for_status()
            payload = response.json()
        voices: list[VoiceOption] = []
        for speaker in payload:
            speaker_name = speaker.get("name", "Unknown")
            styles = speaker.get("styles", [])
            for style in styles:
                voices.append(
                    VoiceOption(
                        id=str(style["id"]),
                        label=f"{speaker_name} / {style.get('name', 'Style')}",
                        language="Japanese",
                        locale="ja-JP",
                        voice_type="character",
                        description=speaker_name,
                        styles=[style.get("name", "Style")],
                        tags=["voicevox", "self-hosted", "character"],
                        metadata={
                            "speaker_uuid": speaker.get("speaker_uuid"),
                            "speaker_name": speaker_name,
                            "style_name": style.get("name"),
                        },
                    )
                )
        return voices

    def synthesize(self, *, text: str, voice_id: str, output_format: str = "wav", params: dict | None = None) -> SynthesisResult:
        params = params or {}
        speaker = int(voice_id)
        with httpx.Client(timeout=settings.voicevox_timeout_seconds) as client:
            query_response = client.post(
                f"{self._base_url()}/audio_query",
                params={"text": text, "speaker": speaker},
            )
            query_response.raise_for_status()
            query = query_response.json()
            for key in ("speedScale", "pitchScale", "intonationScale", "volumeScale", "prePhonemeLength", "postPhonemeLength"):
                if key in params:
                    query[key] = params[key]
            synth_response = client.post(
                f"{self._base_url()}/synthesis",
                params={"speaker": speaker},
                json=query,
            )
            synth_response.raise_for_status()
        return SynthesisResult(
            audio_bytes=synth_response.content,
            mime_type="audio/wav",
            file_extension="wav",
            provider_metadata={"speaker_id": speaker},
        )
