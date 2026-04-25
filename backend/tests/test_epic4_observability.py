"""Smoke tests for Epic 4 — /v1 versioning, metrics, rate limiter, storage."""

from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voiceforge import config as config_module
from voiceforge import rate_limit as rate_limit_module
from voiceforge.api_router import build_api_router
from voiceforge.db import Base, engine
from voiceforge.observability import render_metrics


@pytest.fixture(autouse=True)
def _ensure_schema_and_reset_state(monkeypatch):
    Base.metadata.create_all(bind=engine)
    rate_limit_module.reset_rate_limit_state()
    monkeypatch.setattr(config_module.settings, "rate_limit_per_minute", 0, raising=False)
    yield
    rate_limit_module.reset_rate_limit_state()


def _client() -> TestClient:
    """Build a FastAPI app with both the legacy and /v1 mounts, like main.py does."""
    app = FastAPI()
    app.include_router(build_api_router(), prefix="/v1")
    app.include_router(build_api_router())
    return TestClient(app)


def test_v1_mount_serves_health() -> None:
    client = _client()
    assert client.get("/health").status_code == 200
    assert client.get("/v1/health").status_code == 200


def test_metrics_render_returns_prometheus_format() -> None:
    body, content_type = render_metrics()
    assert b"voiceforge_http_requests_total" in body
    assert content_type.startswith("text/plain")


def test_rate_limit_blocks_after_threshold(monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "rate_limit_per_minute", 3, raising=False)
    client = _client()
    statuses = [client.get("/v1/projects").status_code for _ in range(6)]
    assert 429 in statuses
    # First 3 should not be 429 (rate window is per minute).
    assert statuses[:3].count(429) == 0


def test_rate_limit_disabled_when_zero(monkeypatch) -> None:
    monkeypatch.setattr(config_module.settings, "rate_limit_per_minute", 0, raising=False)
    client = _client()
    statuses = [client.get("/v1/projects").status_code for _ in range(10)]
    assert 429 not in statuses


def test_local_storage_round_trip(tmp_path) -> None:
    from voiceforge.services.storage import LocalArtifactStorage

    storage = LocalArtifactStorage(tmp_path)
    url = storage.write_bytes("audio/clip.wav", b"hello")
    assert url == "/artifacts/audio/clip.wav"
    assert storage.exists("audio/clip.wav")
    assert storage.read_bytes("audio/clip.wav") == b"hello"

    stream = io.BytesIO(b"stream-bytes")
    storage.write_stream("audio/clip2.wav", stream)
    assert storage.read_bytes("audio/clip2.wav") == b"stream-bytes"

    storage.delete("audio/clip.wav")
    assert not storage.exists("audio/clip.wav")


def test_storage_resolver_defaults_to_local(monkeypatch) -> None:
    from voiceforge.services import storage as storage_module

    monkeypatch.setattr(config_module.settings, "storage_backend", "local", raising=False)
    monkeypatch.setattr(storage_module, "_storage_instance", {}, raising=False)
    backend = storage_module.get_storage()
    assert isinstance(backend, storage_module.LocalArtifactStorage)
