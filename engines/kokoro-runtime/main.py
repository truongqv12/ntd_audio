from __future__ import annotations

import io
import os
import subprocess
import tempfile
from functools import lru_cache
from typing import Any

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from kokoro import KPipeline
from pydantic import BaseModel

app = FastAPI(title="VoiceForge Kokoro Runtime", version="0.1.0")

VOICE_CATALOG = [
    ("af_alloy", "Alloy", "English", "en-US", "female"),
    ("af_aoede", "Aoede", "English", "en-US", "female"),
    ("af_bella", "Bella", "English", "en-US", "female"),
    ("af_heart", "Heart", "English", "en-US", "female"),
    ("af_jessica", "Jessica", "English", "en-US", "female"),
    ("af_kore", "Kore", "English", "en-US", "female"),
    ("bf_alice", "Alice", "English", "en-GB", "female"),
    ("bf_emma", "Emma", "English", "en-GB", "female"),
    ("bf_isabella", "Isabella", "English", "en-GB", "female"),
    ("bf_lily", "Lily", "English", "en-GB", "female"),
    ("bm_daniel", "Daniel", "English", "en-GB", "male"),
    ("bm_fable", "Fable", "English", "en-GB", "male"),
    ("bm_george", "George", "English", "en-GB", "male"),
    ("bm_lewis", "Lewis", "English", "en-GB", "male"),
]

LANG_CODE_BY_PREFIX = {
    "a": "a",
    "b": "b",
}

SAMPLE_RATE = 24000


class SynthesizeRequest(BaseModel):
    text: str
    voice: str
    format: str = "wav"
    speed: float = 1.0


def _voice_catalog() -> list[dict[str, Any]]:
    rows = []
    for voice_id, label, language, locale, gender in VOICE_CATALOG:
        rows.append(
            {
                "id": voice_id,
                "label": label,
                "language": language,
                "locale": locale,
                "gender": gender,
                "voice_type": "narration",
                "description": f"Official Kokoro voice: {label}",
                "styles": ["neutral"],
                "tags": ["kokoro", "open-weight", language.lower()],
                "metadata": {"lang_code": voice_id[0]},
            }
        )
    return rows


@lru_cache(maxsize=8)
def _get_pipeline(lang_code: str) -> KPipeline:
    return KPipeline(lang_code=lang_code)


def _to_audio_bytes(text: str, voice: str, speed: float, target_format: str) -> tuple[bytes, str, str]:
    prefix = voice[0]
    lang_code = LANG_CODE_BY_PREFIX.get(prefix)
    if not lang_code:
        raise HTTPException(status_code=400, detail=f"Unsupported Kokoro voice/lang prefix: {voice}")

    pipeline = _get_pipeline(lang_code)
    chunks = []
    try:
        generator = pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+")
        for _, _, audio in generator:
            chunks.append(np.asarray(audio, dtype=np.float32))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not chunks:
        raise HTTPException(status_code=500, detail="Kokoro returned no audio chunks")

    merged = np.concatenate(chunks)
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "output.wav")
        sf.write(wav_path, merged, SAMPLE_RATE)
        normalized = (target_format or "wav").lower()
        if normalized == "wav":
            with open(wav_path, "rb") as handle:
                return handle.read(), "audio/wav", "wav"
        if normalized != "mp3":
            raise HTTPException(status_code=400, detail=f"Unsupported Kokoro output format: {normalized}")
        mp3_path = os.path.join(tmpdir, "output.mp3")
        subprocess.run(["ffmpeg", "-y", "-i", wav_path, mp3_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open(mp3_path, "rb") as handle:
            return handle.read(), "audio/mpeg", "mp3"


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "engine": "kokoro", "voices": len(VOICE_CATALOG)}


@app.get("/voices")
def voices() -> dict[str, Any]:
    return {"voices": _voice_catalog()}


@app.post("/synthesize")
def synthesize(payload: SynthesizeRequest):
    audio_bytes, mime_type, extension = _to_audio_bytes(payload.text, payload.voice, payload.speed, payload.format)
    return Response(content=audio_bytes, media_type=mime_type, headers={"x-audio-extension": extension})
