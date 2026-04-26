"""Tests for the per-provider concurrency limiter (T2.7)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import pytest


@dataclass
class _StubProvider:
    key: str
    category: str


@pytest.fixture(autouse=True)
def _reset() -> None:
    from voiceforge.services_provider_concurrency import reset_for_tests

    reset_for_tests()
    yield
    reset_for_tests()


def test_default_cloud_limit() -> None:
    from voiceforge.services_provider_concurrency import get_provider_concurrency_limit

    assert get_provider_concurrency_limit("openai", "cloud") == 4


def test_default_self_hosted_limit() -> None:
    from voiceforge.services_provider_concurrency import get_provider_concurrency_limit

    assert get_provider_concurrency_limit("voicevox", "self_hosted") == 1


def test_override_takes_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    from voiceforge.config import settings
    from voiceforge.services_provider_concurrency import get_provider_concurrency_limit

    monkeypatch.setattr(settings, "provider_concurrency_overrides", {"openai": 7})
    assert get_provider_concurrency_limit("openai", "cloud") == 7


def test_override_below_one_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    from voiceforge.config import settings
    from voiceforge.services_provider_concurrency import get_provider_concurrency_limit

    monkeypatch.setattr(settings, "provider_concurrency_overrides", {"openai": 0})
    assert get_provider_concurrency_limit("openai", "cloud") == 1


def test_semaphore_caps_concurrent_synthesis(monkeypatch: pytest.MonkeyPatch) -> None:
    from voiceforge.config import settings
    from voiceforge.services_provider_concurrency import get_provider_semaphore, reset_for_tests

    monkeypatch.setattr(settings, "provider_concurrency_overrides", {"voicevox": 2})
    reset_for_tests()

    provider = _StubProvider(key="voicevox", category="self_hosted")
    sem = get_provider_semaphore(provider)
    in_flight = 0
    peak = 0
    lock = threading.Lock()
    barrier = threading.Event()

    def _work() -> None:
        nonlocal in_flight, peak
        with sem:
            with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            barrier.wait(timeout=2.0)
            time.sleep(0.05)
            with lock:
                in_flight -= 1

    threads = [threading.Thread(target=_work) for _ in range(8)]
    for t in threads:
        t.start()
    time.sleep(0.1)
    barrier.set()
    for t in threads:
        t.join(timeout=5)

    assert peak == 2


def test_get_active_limits_returns_seen_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    from voiceforge.services_provider_concurrency import (
        get_active_limits,
        get_provider_semaphore,
        reset_for_tests,
    )

    reset_for_tests()
    get_provider_semaphore(_StubProvider(key="openai", category="cloud"))
    get_provider_semaphore(_StubProvider(key="voicevox", category="self_hosted"))

    active = get_active_limits()
    assert active == {"openai": 4, "voicevox": 1}
