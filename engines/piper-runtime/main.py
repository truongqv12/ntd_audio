from __future__ import annotations

import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="VoiceForge Piper Runtime", version="0.1.0")

DATA_DIR = Path(os.getenv("PIPER_DATA_DIR", "/data/piper"))
VOICE_IDS = [item.strip() for item in os.getenv("PIPER_VOICE_IDS", "").split(",") if item.strip()]
DOWNLOAD_ON_START = os.getenv("PIPER_DOWNLOAD_ON_START", "false").lower() in {"1", "true", "yes"}
PIPER_MODULE = os.getenv("PIPER_MODULE", "piper")

DATA_DIR.mkdir(parents=True, exist_ok=True)

LANGUAGE_NAMES = {
    "en": "English",
    "vi": "Vietnamese",
    "ja": "Japanese",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese",
}


class SynthesizeRequest(BaseModel):
    text: str
    voice: str
    format: str = "wav"
    speed: float | None = None
    length_scale: float | None = None
    speaker_id: int | None = None


def _run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, check=True)


def _download_voice(voice_id: str) -> None:
    command = ["python", "-m", "piper.download_voices", voice_id, "--data-dir", str(DATA_DIR)]
    _run(command)


def _discover_models() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(DATA_DIR.rglob("*.onnx")):
        voice_id = path.stem
        locale_bits = voice_id.split("-")[0].split("_")
        language_code = locale_bits[0] if locale_bits else ""
        locale = None
        if len(locale_bits) >= 2:
            locale = f"{locale_bits[0]}-{locale_bits[1]}"
        label = voice_id.replace("-", " ").replace("_", " ").title()
        items.append(
            {
                "id": voice_id,
                "label": label,
                "language": LANGUAGE_NAMES.get(language_code, language_code or None),
                "locale": locale,
                "voice_type": "narration",
                "description": f"Local Piper voice model: {voice_id}",
                "styles": ["neutral"],
                "tags": ["piper", "offline", "local"],
                "metadata": {
                    "model_path": str(path),
                    "config_path": str(path.with_suffix(path.suffix + ".json")),
                },
            }
        )
    return items


def _ensure_bootstrap_models() -> None:
    if not DOWNLOAD_ON_START:
        return
    existing = {item["id"] for item in _discover_models()}
    for voice_id in VOICE_IDS:
        if voice_id in existing:
            continue
        try:
            _download_voice(voice_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[piper-runtime] failed to download {voice_id}: {exc}")


def _convert_if_needed(source_wav: Path, target_format: str) -> tuple[bytes, str, str]:
    normalized = (target_format or "wav").lower()
    if normalized == "wav":
        return source_wav.read_bytes(), "audio/wav", "wav"
    if normalized != "mp3":
        raise HTTPException(status_code=400, detail=f"Unsupported Piper output format: {normalized}")
    fd, temp_mp3 = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    temp_mp3_path = Path(temp_mp3)
    try:
        _run(["ffmpeg", "-y", "-i", str(source_wav), str(temp_mp3_path)])
        return temp_mp3_path.read_bytes(), "audio/mpeg", "mp3"
    finally:
        temp_mp3_path.unlink(missing_ok=True)


@app.on_event("startup")
def startup_event() -> None:
    _ensure_bootstrap_models()


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        result = _run(["python", "-m", PIPER_MODULE, "--help"])
        available = len(_discover_models())
        return {"status": "ok", "engine": "piper", "voices": available, "stdout": result.stdout[:0].decode("utf-8", errors="ignore")}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "engine": "piper", "detail": str(exc)}


@app.get("/voices")
def voices() -> dict[str, Any]:
    return {"voices": _discover_models()}


@app.post("/voices/download")
def download_voice(payload: dict[str, str]) -> dict[str, Any]:
    voice_id = payload.get("voice_id", "").strip()
    if not voice_id:
        raise HTTPException(status_code=400, detail="voice_id is required")
    _download_voice(voice_id)
    return {"status": "ok", "voice_id": voice_id}


@app.post("/synthesize")
def synthesize(payload: SynthesizeRequest):
    available = {item["id"] for item in _discover_models()}
    if payload.voice not in available:
        if DOWNLOAD_ON_START or payload.voice in VOICE_IDS:
            _download_voice(payload.voice)
            available = {item["id"] for item in _discover_models()}
        if payload.voice not in available:
            raise HTTPException(status_code=404, detail=f"Voice not installed: {payload.voice}")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_wav = Path(tmpdir) / "output.wav"
        command = [
            "python",
            "-m",
            PIPER_MODULE,
            "-m",
            payload.voice,
            "--data-dir",
            str(DATA_DIR),
            "-f",
            str(output_wav),
        ]
        if payload.speaker_id is not None:
            command.extend(["--speaker", str(payload.speaker_id)])
        length_scale = payload.length_scale if payload.length_scale is not None else payload.speed
        if length_scale is not None:
            command.extend(["--length_scale", str(length_scale)])
        command.extend(["--", payload.text])
        try:
            _run(command)
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="ignore") or exc.stdout.decode("utf-8", errors="ignore")
            raise HTTPException(status_code=500, detail=detail) from exc

        audio_bytes, mime_type, extension = _convert_if_needed(output_wav, payload.format)
        return Response(content=audio_bytes, media_type=mime_type, headers={"x-audio-extension": extension})
