"""T3.9 — third-party provider entry-point discovery."""

from __future__ import annotations

from voiceforge import provider_registry
from voiceforge.providers_base import ProviderCapabilities


class _StubProvider:
    key = "stub"
    name = "Stub"

    capabilities = ProviderCapabilities()

    def list_voices(self):
        return []


class _StubEntryPoint:
    def __init__(self, name: str, target: object) -> None:
        self.name = name
        self._target = target

    def load(self) -> object:
        return self._target


def _install_eps(monkeypatch, eps: list[_StubEntryPoint]) -> None:
    monkeypatch.setattr(provider_registry, "entry_points", lambda group: eps)


def test_plugin_is_discovered(monkeypatch):
    _install_eps(monkeypatch, [_StubEntryPoint("stub", _StubProvider)])
    provider_registry.reload_providers()
    assert "stub" in provider_registry.PROVIDERS
    # Re-build with no plugins so other tests don't see the stub.
    _install_eps(monkeypatch, [])
    provider_registry.reload_providers()


def test_plugin_cannot_shadow_builtin(monkeypatch):
    _install_eps(monkeypatch, [_StubEntryPoint("piper", _StubProvider)])
    provider_registry.reload_providers()
    # Built-in piper survives.
    assert provider_registry.PROVIDERS["piper"].__class__.__name__ == "PiperProvider"
    _install_eps(monkeypatch, [])
    provider_registry.reload_providers()


def test_broken_plugin_is_skipped(monkeypatch):
    class _Boom(_StubEntryPoint):
        def load(self):
            raise RuntimeError("kaboom")

    _install_eps(monkeypatch, [_Boom("broken", None), _StubEntryPoint("stub", _StubProvider)])
    provider_registry.reload_providers()
    assert "stub" in provider_registry.PROVIDERS
    assert "broken" not in provider_registry.PROVIDERS
    _install_eps(monkeypatch, [])
    provider_registry.reload_providers()
