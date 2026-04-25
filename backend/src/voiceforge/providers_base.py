from dataclasses import asdict, dataclass, field
from typing import Protocol


@dataclass(slots=True)
class ProviderCapabilities:
    batch_generation: bool = True
    realtime_generation: bool = False
    local_inference: bool = False
    cloud_api: bool = False
    custom_voice: bool = False
    voice_cloning: bool = False
    expressive_speech: bool = False
    multilingual: bool = False
    requires_gpu: bool = False
    supports_preview_audio: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class VoiceOption:
    id: str
    label: str
    language: str | None = None
    locale: str | None = None
    gender: str | None = None
    voice_type: str | None = None
    description: str | None = None
    accent: str | None = None
    age: str | None = None
    styles: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    preview_url: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class SynthesisResult:
    audio_bytes: bytes
    mime_type: str
    file_extension: str
    duration_seconds: float | None = None
    provider_metadata: dict = field(default_factory=dict)


class VoiceProvider(Protocol):
    key: str
    label: str
    category: str
    capabilities: ProviderCapabilities

    def is_configured(self) -> bool: ...
    def healthcheck(self) -> tuple[bool, str]: ...
    def list_voices(self) -> list[VoiceOption]: ...
    def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        output_format: str = "mp3",
        params: dict | None = None,
    ) -> SynthesisResult: ...
