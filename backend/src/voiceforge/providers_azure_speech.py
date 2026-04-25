import html

import httpx

from .config import settings
from .providers_base import ProviderCapabilities, SynthesisResult, VoiceOption
from .runtime_settings import get_provider_runtime_config


class AzureSpeechProvider:
    key = "azure_speech"
    label = "Azure Speech"
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
            "azure_speech_key": cfg.get("azure_speech_key") or settings.azure_speech_key,
            "azure_speech_region": cfg.get("azure_speech_region") or settings.azure_speech_region,
        }

    def _voices_url(self) -> str:
        return f"https://{self._cfg().get('azure_speech_region')}.tts.speech.microsoft.com/cognitiveservices/voices/list"

    def _tts_url(self) -> str:
        return f"https://{self._cfg().get('azure_speech_region')}.tts.speech.microsoft.com/cognitiveservices/v1"

    def is_configured(self) -> bool:
        cfg = self._cfg()
        return bool(cfg.get("azure_speech_key") and cfg.get("azure_speech_region"))

    def healthcheck(self) -> tuple[bool, str]:
        cfg = self._cfg()
        if not self.is_configured():
            return False, "AZURE_SPEECH_KEY or AZURE_SPEECH_REGION missing"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    self._voices_url(),
                    headers={"Ocp-Apim-Subscription-Key": cfg.get("azure_speech_key")},
                )
                response.raise_for_status()
            return True, "Configured"
        except Exception as exc:
            return False, str(exc)

    def list_voices(self) -> list[VoiceOption]:
        cfg = self._cfg()
        if not self.is_configured():
            return []
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                self._voices_url(),
                headers={"Ocp-Apim-Subscription-Key": cfg.get("azure_speech_key")},
            )
            response.raise_for_status()
            payload = response.json()
        voices = []
        for item in payload:
            voices.append(
                VoiceOption(
                    id=item.get("ShortName", ""),
                    label=item.get("DisplayName", item.get("ShortName", "")),
                    language=item.get("LocaleName"),
                    locale=item.get("Locale"),
                    gender=item.get("Gender"),
                    voice_type="neural" if item.get("VoiceType") == "Neural" else item.get("VoiceType"),
                    description=item.get("StyleList", ["Azure Speech voice"])[0] if item.get("StyleList") else "Azure Speech voice",
                    styles=item.get("StyleList") or [],
                    tags=["cloud", "azure", "multilingual"],
                    metadata={"status": item.get("Status"), "sampleRateHertz": item.get("SampleRateHertz")},
                )
            )
        return voices

    def synthesize(self, *, text: str, voice_id: str, output_format: str = "mp3", params: dict | None = None) -> SynthesisResult:
        cfg = self._cfg()
        if not self.is_configured():
            raise RuntimeError("Azure speech not configured")
        locale = (params or {}).get("locale") or "-".join(voice_id.split("-")[:2]) or "en-US"
        safe_text = html.escape(text)
        prosody_attrs = []
        if params and params.get("rate") not in (None, "", 0):
            prosody_attrs.append(f"rate='{float(params['rate']):+g}%'")
        if params and params.get("pitch") not in (None, "", 0):
            prosody_attrs.append(f"pitch='{float(params['pitch']):+g}%'")
        if params and params.get("volume") not in (None, "", 0):
            prosody_attrs.append(f"volume='{float(params['volume']):+g}%'")
        body = safe_text
        if prosody_attrs:
            body = f"<prosody {' '.join(prosody_attrs)}>{safe_text}</prosody>"
        if params and params.get("style"):
            body = f"<mstts:express-as style='{html.escape(str(params['style']))}'>{body}</mstts:express-as>"
        ssml = f"""
<speak version='1.0' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='{locale}'>
  <voice name='{voice_id}'>{body}</voice>
</speak>
""".strip()
        output_header = (
            "audio-24khz-48kbitrate-mono-mp3"
            if output_format == "mp3"
            else "riff-24khz-16bit-mono-pcm"
        )
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self._tts_url(),
                headers={
                    "Ocp-Apim-Subscription-Key": cfg.get("azure_speech_key"),
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": output_header,
                },
                content=ssml.encode("utf-8"),
            )
            response.raise_for_status()
        return SynthesisResult(
            audio_bytes=response.content,
            mime_type="audio/mpeg" if output_format == "mp3" else "audio/wav",
            file_extension="mp3" if output_format == "mp3" else "wav",
            provider_metadata={"voice_name": voice_id, "locale": locale},
        )
