"""Redis pub/sub fan-out for live job/event signals.

Producers (services_jobs.create_job/cancel_job/retry_job, worker on
state transitions) call ``publish_jobs_changed(reason)`` after committing.
Consumers (the SSE /events/stream endpoint) call ``subscribe_jobs_changed``
to get an async iterator of small JSON notifications and only re-query the
DB when a message arrives — so we get sub-second updates without DB polling.

Both sides degrade gracefully: if Redis is unreachable, ``publish`` becomes a
warn-once no-op and ``subscribe`` falls back to a slow heartbeat so the SSE
loop still ticks (and still picks up updates via its existing signature
fallback).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import redis
import redis.asyncio as redis_async

from .config import settings

logger = logging.getLogger(__name__)

CHANNEL = "voiceforge:jobs"

_warned: dict[str, bool] = {"sync": False}
_sync_client_cache: dict[str, redis.Redis | None] = {}


def _sync_client() -> redis.Redis | None:
    """Return a lazily-built module-level Redis client (or None if unreachable).

    Reusing a single client avoids leaking a fresh ``ConnectionPool`` on every
    job state transition. Failures are *not* cached as ``None`` — the next
    publish retries ``from_url`` so a transient outage at startup recovers
    automatically. Warnings are rate-limited via ``_warned`` so logs don't
    flood when Redis stays down.
    """
    cached = _sync_client_cache.get("client")
    if cached is not None:
        return cached
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as exc:
        if not _warned["sync"]:
            logger.warning("events_bus_sync_unavailable url=%s err=%s", settings.redis_url, exc)
            _warned["sync"] = True
        return None
    _sync_client_cache["client"] = client
    _warned["sync"] = False  # reset so a future outage gets a fresh warning
    return client


def publish_jobs_changed(reason: str, *, payload: dict | None = None) -> None:
    """Fire-and-forget notification. Never raises — Redis going down can't break a job commit.

    Note on metrics: this function does NOT record Prometheus metrics directly,
    because publishers run in two processes — the API and the Dramatiq worker —
    and each owns a separate in-memory ``REGISTRY``. If we recorded here, the
    worker's increments/decrements would never reach the API's ``/metrics``
    endpoint, and the in-flight gauge would only ever climb. Instead, the API
    runs a single subscriber loop (see ``main._metrics_subscriber``) that reads
    every message off the Redis channel and updates metrics there.
    """
    client = _sync_client()
    if client is None:
        return
    body = json.dumps({"reason": reason, "payload": payload or {}}, ensure_ascii=False)
    try:
        client.publish(CHANNEL, body)
    except Exception as exc:
        logger.warning("events_bus_publish_failed reason=%s err=%s", reason, exc)
        # Drop the cached client so the next call rebuilds it after a transient outage.
        _sync_client_cache.pop("client", None)


async def subscribe_jobs_changed(heartbeat_seconds: float = 15.0) -> AsyncIterator[dict]:
    """Yield messages as they arrive on the channel.

    Yields ``{"reason": str, "payload": dict}`` for real notifications and
    ``{"reason": "heartbeat"}`` every ``heartbeat_seconds`` so the caller can
    trigger keepalive / reconnect logic. If Redis is unreachable, only
    heartbeats are yielded.
    """
    client: redis_async.Redis | None = None
    pubsub: redis_async.client.PubSub | None = None
    try:
        try:
            client = redis_async.from_url(settings.redis_url, decode_responses=True)
            assert client is not None  # narrow for mypy across the try/except split
            pubsub = client.pubsub()
            await pubsub.subscribe(CHANNEL)
        except Exception as exc:
            logger.warning("events_bus_subscribe_unavailable url=%s err=%s", settings.redis_url, exc)
            # Subscribe failed — fall back to heartbeat-only. The outer finally
            # still runs and closes whatever managed to get created.
            while True:
                await asyncio.sleep(heartbeat_seconds)
                yield {"reason": "heartbeat"}

        while True:
            # redis-py's get_message blocks up to ``timeout`` seconds when no
            # message is pending; passing 0/None would hot-spin the loop.
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=heartbeat_seconds)
            if message is None:
                yield {"reason": "heartbeat"}
                continue
            data = message.get("data")
            if not data:
                continue
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                logger.warning("events_bus_invalid_payload data=%r", data)
    finally:
        if pubsub is not None:
            try:
                await pubsub.close()
            except Exception:
                pass
        if client is not None:
            try:
                await client.close()
            except Exception:
                pass
