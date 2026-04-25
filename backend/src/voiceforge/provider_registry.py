from .providers_azure_speech import AzureSpeechProvider
from .providers_elevenlabs import ElevenLabsProvider
from .providers_google_tts import GoogleCloudTTSProvider
from .providers_piper import PiperProvider
from .providers_kokoro import KokoroProvider
from .providers_vieneu_tts import VieNeuTTSProvider
from .providers_openai_tts import OpenAITTSProvider
from .providers_voicevox import VoicevoxProvider

PROVIDERS = {
    "voicevox": VoicevoxProvider(),
    "piper": PiperProvider(),
    "kokoro": KokoroProvider(),
    "vieneu_tts": VieNeuTTSProvider(),
    "openai_tts": OpenAITTSProvider(),
    "elevenlabs": ElevenLabsProvider(),
    "google_cloud_tts": GoogleCloudTTSProvider(),
    "azure_speech": AzureSpeechProvider(),
}


def get_provider(key: str):
    if key not in PROVIDERS:
        raise KeyError(f"Unknown provider: {key}")
    return PROVIDERS[key]


def list_providers():
    return list(PROVIDERS.values())
