import base64

import httpx

from .config import settings
from .providers_base import ProviderCapabilities, SynthesisResult, VoiceOption
from .runtime_settings import get_provider_runtime_config


class GoogleCloudTTSProvider:
    key = "google_cloud_tts"
    label = "Google Cloud TTS"
    category = "cloud"
    capabilities = ProviderCapabilities(
        batch_generation=True,
        realtime_generation=True,
        local_inference=False,
        cloud_api=True,
        custom_voice=True,
        expressive_speech=True,
        multilingual=True,
        supports_preview_audio=False,
    )

    def _cfg(self) -> dict:
        cfg = get_provider_runtime_config(self.key)
        return {
            "google_tts_access_token": cfg.get("google_tts_access_token") or settings.google_tts_access_token,
            "google_tts_project_id": cfg.get("google_tts_project_id") or settings.google_tts_project_id,
        }

    def is_configured(self) -> bool:
        return bool(self._cfg().get("google_tts_access_token"))

    def healthcheck(self) -> tuple[bool, str]:
        cfg = self._cfg()
        if not cfg.get("google_tts_access_token"):
            return False, "GOOGLE_TTS_ACCESS_TOKEN missing"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    "https://texttospeech.googleapis.com/v1/voices",
                    headers={"Authorization": f"Bearer {cfg.get('google_tts_access_token')}"},
                )
                response.raise_for_status()
            return True, "Configured"
        except Exception as exc:
            return False, str(exc)

    def list_voices(self) -> list[VoiceOption]:
        cfg = self._cfg()
        if not cfg.get("google_tts_access_token"):
            return []
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                "https://texttospeech.googleapis.com/v1/voices",
                headers={"Authorization": f"Bearer {cfg.get('google_tts_access_token')}"},
            )
            response.raise_for_status()
            payload = response.json()
        voices = []
        for item in payload.get("voices", []):
            locale = (item.get("languageCodes") or [""])[0]
            voices.append(
                VoiceOption(
                    id=item.get("name", ""),
                    label=item.get("name", ""),
                    language=locale.split("-")[0] if locale else None,
                    locale=locale,
                    gender=item.get("ssmlGender"),
                    voice_type="neural" if "Chirp" in item.get("name", "") else "standard",
                    description="Google Cloud TTS voice",
                    tags=["cloud", "google", "multilingual"],
                    metadata={"naturalSampleRateHertz": item.get("naturalSampleRateHertz")},
                )
            )
        return voices

    def synthesize(
        self, *, text: str, voice_id: str, output_format: str = "mp3", params: dict | None = None
    ) -> SynthesisResult:
        cfg = self._cfg()
        if not cfg.get("google_tts_access_token"):
            raise RuntimeError("GOOGLE_TTS_ACCESS_TOKEN missing")
        locale = (params or {}).get("locale") or "-".join(voice_id.split("-")[:2]) or "en-US"
        audio_encoding = "MP3" if output_format == "mp3" else "LINEAR16"
        audio_config = {"audioEncoding": audio_encoding}
        for src, dst in (
            ("speakingRate", "speakingRate"),
            ("speaking_rate", "speakingRate"),
            ("pitch", "pitch"),
            ("volumeGainDb", "volumeGainDb"),
            ("volume_gain_db", "volumeGainDb"),
            ("sampleRateHertz", "sampleRateHertz"),
        ):
            if params and params.get(src) not in (None, "", 0 if src == "sampleRateHertz" else None):
                audio_config[dst] = params[src]
        advanced = {}
        if params and params.get("lowLatencyJourneySynthesis") not in (None, ""):
            advanced["lowLatencyJourneySynthesis"] = bool(params.get("lowLatencyJourneySynthesis"))
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "https://texttospeech.googleapis.com/v1/text:synthesize",
                headers={"Authorization": f"Bearer {cfg.get('google_tts_access_token')}"},
                json={
                    "input": {"text": text},
                    "voice": {"languageCode": locale, "name": voice_id},
                    "audioConfig": audio_config,
                    **({"advancedVoiceOptions": advanced} if advanced else {}),
                },
            )
            response.raise_for_status()
            payload = response.json()
        content = base64.b64decode(payload["audioContent"])
        return SynthesisResult(
            audio_bytes=content,
            mime_type="audio/mpeg" if output_format == "mp3" else "audio/wav",
            file_extension="mp3" if output_format == "mp3" else "wav",
            provider_metadata={"voice_name": voice_id, "locale": locale},
        )
