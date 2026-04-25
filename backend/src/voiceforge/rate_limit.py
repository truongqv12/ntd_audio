"""Lightweight in-process rate limiter (Epic 4).

Token-bucket / fixed-window hybrid: each client (identified by API key when
present, otherwise the remote IP) gets ``RATE_LIMIT_PER_MINUTE`` requests per
rolling 60s window. Disabled when the env var is 0 / missing.

This is intentionally not Redis-backed — single-host deployments do not need
distributed limits, and the overhead of a per-request Redis round-trip is real.
For multi-instance deployments, swap this for ``slowapi`` or a dedicated
sidecar.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from .config import settings

_WINDOW_SECONDS = 60.0
_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()
_last_sweep: float = 0.0


def _client_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"k:{api_key}"
    if request.client and request.client.host:
        return f"ip:{request.client.host}"
    return "anon"


def _sweep_stale_buckets(cutoff: float) -> None:
    """Drop any bucket whose newest hit is older than the window.

    Keeps ``_buckets`` bounded under high-cardinality traffic (botnets,
    scanners). Caller must hold ``_lock``.
    """
    stale = [key for key, bucket in _buckets.items() if not bucket or bucket[-1] < cutoff]
    for key in stale:
        _buckets.pop(key, None)


def check_rate_limit(request: Request) -> None:
    """FastAPI dependency: 429 when the caller exceeds the configured rate."""
    global _last_sweep
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return

    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    key = _client_key(request)

    with _lock:
        if now - _last_sweep > _WINDOW_SECONDS:
            _sweep_stale_buckets(cutoff)
            _last_sweep = now
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, int(bucket[0] + _WINDOW_SECONDS - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


def reset_rate_limit_state() -> None:
    """Test helper: clear all buckets."""
    global _last_sweep
    with _lock:
        _buckets.clear()
        _last_sweep = 0.0
