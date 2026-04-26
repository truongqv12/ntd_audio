from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

ParamKind = Literal["number", "text", "textarea", "boolean", "select"]


@dataclass(slots=True)
class ProviderParamField:
    key: str
    label: str
    kind: ParamKind = "number"
    default: str | float | int | bool | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str | None = None
    description: str | None = None
    options: list[dict[str, str]] = field(default_factory=list)
    advanced: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


COMMON_POST_PARAMS = [
    ProviderParamField(
        "gain_db",
        "Post gain",
        "number",
        0,
        -12,
        12,
        1,
        "dB",
        "Optional post-processing gain. Not applied by every engine.",
        advanced=True,
    ),
]

PARAMETER_SCHEMAS: dict[str, list[ProviderParamField]] = {
    "openai_tts": [
        ProviderParamField("speed", "Speed", "number", 1, 0.25, 4, 0.05, "x", "OpenAI speech speed. 1.0 is normal."),
        ProviderParamField(
            "instructions",
            "Instructions",
            "textarea",
            "",
            None,
            None,
            None,
            None,
            "Optional style/delivery instructions for gpt-4o-mini-tts.",
        ),
    ],
    "elevenlabs": [
        ProviderParamField(
            "speed", "Speed", "number", 1, 0.7, 1.2, 0.01, "x", "ElevenLabs speed. Extreme values can affect quality."
        ),
        ProviderParamField(
            "stability",
            "Stability",
            "number",
            0.5,
            0,
            1,
            0.01,
            None,
            "Higher values are more consistent; lower values are more expressive.",
        ),
        ProviderParamField(
            "similarity_boost",
            "Similarity",
            "number",
            0.75,
            0,
            1,
            0.01,
            None,
            "How closely the output follows the selected voice.",
        ),
        ProviderParamField(
            "style",
            "Style exaggeration",
            "number",
            0,
            0,
            1,
            0.01,
            None,
            "Amplifies style; can increase latency and instability.",
        ),
        ProviderParamField(
            "use_speaker_boost",
            "Speaker boost",
            "boolean",
            True,
            None,
            None,
            None,
            None,
            "Improves speaker similarity with extra compute.",
        ),
    ],
    "google_cloud_tts": [
        ProviderParamField(
            "speakingRate", "Speaking rate", "number", 1, 0.25, 2, 0.05, "x", "Google audioConfig.speakingRate."
        ),
        ProviderParamField("pitch", "Pitch", "number", 0, -20, 20, 0.5, "st", "Google audioConfig.pitch in semitones."),
        ProviderParamField(
            "volumeGainDb", "Volume gain", "number", 0, -96, 16, 1, "dB", "Google audioConfig.volumeGainDb."
        ),
        ProviderParamField(
            "sampleRateHertz",
            "Sample rate",
            "number",
            0,
            0,
            48000,
            1000,
            "Hz",
            "Optional output sample rate. 0 means provider default.",
            advanced=True,
        ),
        ProviderParamField(
            "lowLatencyJourneySynthesis",
            "Journey low latency",
            "boolean",
            False,
            None,
            None,
            None,
            None,
            "Only for Journey voices.",
            advanced=True,
        ),
    ],
    "azure_speech": [
        ProviderParamField(
            "rate", "Rate", "number", 0, -50, 100, 5, "%", "SSML prosody rate percentage. 0 means default."
        ),
        ProviderParamField(
            "pitch", "Pitch", "number", 0, -50, 50, 5, "%", "SSML prosody pitch percentage. 0 means default."
        ),
        ProviderParamField(
            "volume", "Volume", "number", 0, -50, 50, 5, "%", "SSML prosody volume percentage. 0 means default."
        ),
        ProviderParamField(
            "style",
            "Style",
            "text",
            "",
            None,
            None,
            None,
            None,
            "Optional Azure style name if the voice supports it.",
            advanced=True,
        ),
    ],
    "voicevox": [
        ProviderParamField(
            "speedScale", "Speed scale", "number", 1, 0.5, 2, 0.05, "x", "VOICEVOX audio query speedScale."
        ),
        ProviderParamField("pitchScale", "Pitch scale", "number", 0, -0.15, 0.15, 0.01, None, "VOICEVOX pitchScale."),
        ProviderParamField(
            "intonationScale", "Intonation scale", "number", 1, 0, 2, 0.05, "x", "VOICEVOX intonationScale."
        ),
        ProviderParamField("volumeScale", "Volume scale", "number", 1, 0, 2, 0.05, "x", "VOICEVOX volumeScale."),
        ProviderParamField(
            "prePhonemeLength",
            "Pre-phoneme pause",
            "number",
            0.1,
            0,
            2,
            0.05,
            "s",
            "Pause before speech.",
            advanced=True,
        ),
        ProviderParamField(
            "postPhonemeLength",
            "Post-phoneme pause",
            "number",
            0.1,
            0,
            2,
            0.05,
            "s",
            "Pause after speech.",
            advanced=True,
        ),
    ],
    "piper": [
        ProviderParamField(
            "length_scale",
            "Length scale",
            "number",
            1,
            0.5,
            2,
            0.05,
            "x",
            "Piper length scale; higher usually sounds slower.",
        ),
        ProviderParamField(
            "noise_scale", "Noise scale", "number", 0.667, 0, 1.5, 0.01, None, "Controls variation/randomness in Piper."
        ),
        ProviderParamField(
            "noise_w", "Noise width", "number", 0.8, 0, 1.5, 0.01, None, "Controls phoneme duration noise in Piper."
        ),
        ProviderParamField(
            "speaker_id",
            "Speaker ID",
            "number",
            0,
            0,
            100,
            1,
            None,
            "Optional speaker id for multi-speaker models.",
            advanced=True,
        ),
    ],
    "kokoro": [
        ProviderParamField("speed", "Speed", "number", 1, 0.5, 2, 0.05, "x", "Kokoro runtime speed."),
    ],
    "vieneu_tts": [
        ProviderParamField("speed", "Speed", "number", 1, 0.5, 2, 0.05, "x", "Runtime speed if supported."),
        ProviderParamField(
            "reference_audio_path",
            "Reference audio path",
            "text",
            "",
            None,
            None,
            None,
            None,
            "Optional local reference audio for cloning.",
            advanced=True,
        ),
        ProviderParamField(
            "reference_text",
            "Reference text",
            "textarea",
            "",
            None,
            None,
            None,
            None,
            "Transcript for reference audio if available.",
            advanced=True,
        ),
    ],
}


def get_parameter_schema(provider_key: str) -> list[dict]:
    return [item.to_dict() for item in PARAMETER_SCHEMAS.get(provider_key, [])]


def get_all_parameter_schemas() -> dict[str, list[dict]]:
    return {key: [item.to_dict() for item in value] for key, value in PARAMETER_SCHEMAS.items()}
