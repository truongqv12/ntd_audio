from __future__ import annotations

import os
import subprocess
import tempfile
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from vieneu import Vieneu

app = FastAPI(title="VoiceForge VieNeu Runtime", version="0.1.0")

DEFAULT_LANGUAGE = os.getenv("VIENEU_DEFAULT_LANGUAGE", "Vietnamese")
DEFAULT_LOCALE = os.getenv("VIENEU_DEFAULT_LOCALE", "vi-VN")


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None
    format: str = "wav"
    reference_audio_path: str | None = None
    reference_text: str | None = None


@lru_cache(maxsize=1)
def _client() -> Vieneu:
    return Vieneu()


def _preset_voice_map() -> dict[str, dict[str, Any]]:
    client = _client()
    rows = {}
    for description, voice_id in client.list_preset_voices():
        rows[voice_id] = {
            "id": voice_id,
            "label": description,
            "language": DEFAULT_LANGUAGE,
            "locale": DEFAULT_LOCALE,
            "voice_type": "narration",
            "description": description,
            "styles": ["neutral"],
            "tags": ["vieneu", "vietnamese", "bilingual", "cloning"],
            "metadata": {},
        }
    return rows


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        voice_count = len(_preset_voice_map())
        return {"status": "ok", "engine": "vieneu", "voices": voice_count}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "engine": "vieneu", "detail": str(exc)}


@app.get("/voices")
def voices() -> dict[str, Any]:
    return {"voices": list(_preset_voice_map().values())}


@app.post("/synthesize")
def synthesize(payload: SynthesizeRequest):
    client = _client()
    preset_voice = None
    if payload.voice:
        voice_map = _preset_voice_map()
        if payload.voice not in voice_map:
            raise HTTPException(status_code=404, detail=f"VieNeu preset voice not found: {payload.voice}")
        preset_voice = client.get_preset_voice(payload.voice)

    try:
        if payload.reference_audio_path:
            if not os.path.exists(payload.reference_audio_path):
                raise HTTPException(status_code=400, detail=f"reference_audio_path not found: {payload.reference_audio_path}")
            encoded_voice = client.encode_reference(payload.reference_audio_path)
            audio = client.infer(text=payload.text, voice=encoded_voice)
        elif preset_voice is not None:
            audio = client.infer(text=payload.text, voice=preset_voice)
        else:
            audio = client.infer(text=payload.text)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "output.wav")
        client.save(audio, wav_path)
        normalized = (payload.format or "wav").lower()
        if normalized == "wav":
            with open(wav_path, "rb") as handle:
                return Response(content=handle.read(), media_type="audio/wav", headers={"x-audio-extension": "wav"})
        if normalized != "mp3":
            raise HTTPException(status_code=400, detail=f"Unsupported VieNeu output format: {normalized}")
        mp3_path = os.path.join(tmpdir, "output.mp3")
        subprocess.run(["ffmpeg", "-y", "-i", wav_path, mp3_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open(mp3_path, "rb") as handle:
            return Response(content=handle.read(), media_type="audio/mpeg", headers={"x-audio-extension": "mp3"})
