"""Host capabilities probe (T2.6) — synthesizes nvidia-smi presence and
verifies the response shape and overlay recommendation."""

from __future__ import annotations

import subprocess

import pytest
from fastapi.testclient import TestClient

from voiceforge import services_system


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    services_system.reset_for_tests()
    yield
    services_system.reset_for_tests()


def _client() -> TestClient:
    from voiceforge.api_router import build_api_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(build_api_router())
    return TestClient(app)


def test_probe_returns_no_gpu_when_nvidia_smi_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services_system.shutil, "which", lambda _: None)
    caps = services_system.get_host_capabilities(force_refresh=True)
    assert caps.gpu is None
    assert caps.recommended_overlays == []
    assert caps.cpu.threads >= 1


def test_probe_parses_nvidia_smi_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services_system.shutil, "which", lambda _: "/usr/bin/nvidia-smi")

    class _Result:
        returncode = 0
        stdout = "NVIDIA GeForce RTX 3090, 24576\n"

    monkeypatch.setattr(services_system.subprocess, "run", lambda *a, **kw: _Result())
    caps = services_system.get_host_capabilities(force_refresh=True)
    assert caps.gpu is not None
    assert caps.gpu.vendor == "nvidia"
    assert caps.gpu.name == "NVIDIA GeForce RTX 3090"
    assert caps.gpu.vram_mb == 24576
    assert "docker-compose.gpu.yml" in caps.recommended_overlays


def test_probe_handles_nvidia_smi_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services_system.shutil, "which", lambda _: "/usr/bin/nvidia-smi")

    def _raise(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=2.0)

    monkeypatch.setattr(services_system.subprocess, "run", _raise)
    caps = services_system.get_host_capabilities(force_refresh=True)
    assert caps.gpu is None


def test_probe_caches_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def _which(_: str) -> str | None:
        calls["count"] += 1
        return None

    monkeypatch.setattr(services_system.shutil, "which", _which)
    services_system.get_host_capabilities(force_refresh=True)
    services_system.get_host_capabilities()
    services_system.get_host_capabilities()
    assert calls["count"] == 1


def test_capabilities_endpoint_returns_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services_system.shutil, "which", lambda _: None)
    response = _client().get("/system/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["gpu"] is None
    assert "cores" in body["cpu"]
    assert body["recommended_overlays"] == []
