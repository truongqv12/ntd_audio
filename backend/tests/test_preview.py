"""Tests for the on-demand preview endpoints (T1.4)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeProvider:
    key = "fake"
    label = "Fake"
    category = "self_hosted"
    capabilities = type(
        "C",
        (),
        {
            "to_dict": lambda self: {
                "supports_streaming": False,
                "supports_speed": False,
                "supports_pitch": False,
                "supports_emotion": False,
                "supports_ssml": False,
                "supports_preview_audio": True,
                "max_input_chars": 4000,
                "supported_formats": ["wav"],
            }
        },
    )()

    def is_configured(self) -> bool:
        return True

    def healthcheck(self) -> tuple[bool, str]:
        return True, "ok"

    def list_voices(self) -> list[Any]:
        return []

    def synthesize(self, *, text: str, voice_id: str, output_format: str = "wav", params: dict | None = None):
        from voiceforge.providers_base import SynthesisResult

        return SynthesisResult(audio_bytes=text.encode(), mime_type="audio/wav", file_extension="wav")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, db_session) -> TestClient:
    from voiceforge import routes_providers
    from voiceforge.routes_providers import router as providers_router

    monkeypatch.setattr(routes_providers, "get_provider", lambda key: _FakeProvider())
    monkeypatch.setattr(routes_providers, "apply_provider_settings", lambda db: None)

    app = FastAPI()
    app.include_router(providers_router)
    return TestClient(app)


def test_preview_post_returns_audio_bytes(client: TestClient) -> None:
    response = client.post(
        "/providers/fake/preview",
        json={"text": "Hello world", "voice_id": "fake:1"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"Hello world"


def test_preview_post_rejects_overlong_text(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from voiceforge.config import settings

    monkeypatch.setattr(settings, "preview_max_chars", 10)
    response = client.post(
        "/providers/fake/preview",
        json={"text": "x" * 50, "voice_id": "fake:1"},
    )
    assert response.status_code == 413


def test_preview_post_rejects_empty_text(client: TestClient) -> None:
    response = client.post(
        "/providers/fake/preview",
        json={"text": "", "voice_id": "fake:1"},
    )
    assert response.status_code == 422
