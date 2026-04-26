"""Per-provider concurrency limiter (T2.7).

A process-local semaphore keyed by provider key. Cloud providers default to
4 concurrent calls (network-bound), self-hosted ones to 1 (CPU/GPU-bound,
sharing a single backend). Either default can be overridden via env, and any
provider-specific limit can be set via the ``PROVIDER_CONCURRENCY`` JSON dict.

The semaphore is a ``threading.BoundedSemaphore`` because Dramatiq's default
worker uses a thread pool; the limit therefore applies *within* one worker
process. If you scale by running multiple worker processes, the effective
ceiling is ``worker_count * provider_limit`` — for personal-use single-host
installs this is the right tradeoff (simple, no Redis coordination).
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from .config import settings

if TYPE_CHECKING:
    from .providers_base import VoiceProvider


_lock = threading.Lock()
_semaphores: dict[str, threading.BoundedSemaphore] = {}
_limits: dict[str, int] = {}


def _category_default(category: str) -> int:
    if category == "cloud":
        return settings.provider_concurrency_default_cloud
    return settings.provider_concurrency_default_self_hosted


def get_provider_concurrency_limit(provider_key: str, category: str) -> int:
    """Return the configured concurrency limit for a provider.

    Order of precedence:
    1. ``PROVIDER_CONCURRENCY[provider_key]`` if set.
    2. Per-category default (``cloud`` vs anything else).

    The returned value is always at least 1.
    """
    overrides = settings.provider_concurrency_overrides
    if provider_key in overrides:
        return max(1, overrides[provider_key])
    return max(1, _category_default(category))


def get_provider_semaphore(provider: VoiceProvider) -> threading.BoundedSemaphore:
    """Return a process-local semaphore for the given provider.

    The semaphore is created lazily on first request and cached for the
    lifetime of the process. The limit is captured at creation time and is
    not re-read if env vars change at runtime.
    """
    key = provider.key
    with _lock:
        cached = _semaphores.get(key)
        if cached is not None:
            return cached
        limit = get_provider_concurrency_limit(key, provider.category)
        sem = threading.BoundedSemaphore(value=limit)
        _semaphores[key] = sem
        _limits[key] = limit
        return sem


def get_active_limits() -> dict[str, int]:
    """Return a snapshot of `{provider_key: limit}` for all providers seen so far."""
    with _lock:
        return dict(_limits)


def reset_for_tests() -> None:
    """Clear cached semaphores. Test-only helper."""
    with _lock:
        _semaphores.clear()
        _limits.clear()
