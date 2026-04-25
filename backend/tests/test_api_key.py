"""APP_API_KEYS gate. /health stays public; everything else requires the header when configured."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voiceforge import config as config_module
from voiceforge.api_router import api_router
from voiceforge.db import Base, engine


@pytest.fixture(autouse=True)
def _ensure_schema():
    """The TestClient hits the module-level engine; make sure tables exist on it."""
    Base.metadata.create_all(bind=engine)
    yield


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router)
    return TestClient(app)


def test_health_stays_public_even_when_keys_set(monkeypatch):
    monkeypatch.setattr(config_module.settings, "app_api_keys", ["secret-1"], raising=False)
    response = _client().get("/health")
    assert response.status_code == 200


def test_protected_endpoint_requires_key(monkeypatch):
    monkeypatch.setattr(config_module.settings, "app_api_keys", ["secret-1"], raising=False)
    response = _client().get("/projects")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid X-API-Key"


def test_protected_endpoint_accepts_valid_key(monkeypatch):
    monkeypatch.setattr(config_module.settings, "app_api_keys", ["secret-1", "secret-2"], raising=False)
    response = _client().get("/projects", headers={"X-API-Key": "secret-2"})
    # The endpoint itself may 500/200 depending on DB state; what we're asserting
    # is that the auth dependency did NOT short-circuit with 401.
    assert response.status_code != 401


def test_no_keys_means_open_access(monkeypatch):
    monkeypatch.setattr(config_module.settings, "app_api_keys", [], raising=False)
    response = _client().get("/projects")
    assert response.status_code != 401
