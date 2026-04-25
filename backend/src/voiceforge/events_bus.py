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


def _sync_client() -> redis.Redis | None:
    try:
        return redis.Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as exc:
        if not _warned["sync"]:
            logger.warning("events_bus_sync_unavailable url=%s err=%s", settings.redis_url, exc)
            _warned["sync"] = True
        return None


def publish_jobs_changed(reason: str, *, payload: dict | None = None) -> None:
    """Fire-and-forget notification. Never raises — Redis going down can't break a job commit."""
    client = _sync_client()
    if client is None:
        return
    body = json.dumps({"reason": reason, "payload": payload or {}}, ensure_ascii=False)
    try:
        client.publish(CHANNEL, body)
    except Exception as exc:
        logger.warning("events_bus_publish_failed reason=%s err=%s", reason, exc)


async def subscribe_jobs_changed(heartbeat_seconds: float = 15.0) -> AsyncIterator[dict]:
    """Yield messages as they arrive on the channel.

    Yields ``{"reason": str, "payload": dict}`` for real notifications and
    ``{"reason": "heartbeat"}`` every ``heartbeat_seconds`` so the caller can
    trigger keepalive / reconnect logic. If Redis is unreachable, only
    heartbeats are yielded.
    """
    try:
        client = redis_async.from_url(settings.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(CHANNEL)
    except Exception as exc:
        logger.warning("events_bus_subscribe_unavailable url=%s err=%s", settings.redis_url, exc)
        while True:
            await asyncio.sleep(heartbeat_seconds)
            yield {"reason": "heartbeat"}

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True), timeout=heartbeat_seconds
                )
            except TimeoutError:
                yield {"reason": "heartbeat"}
                continue
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
        try:
            await pubsub.close()
        except Exception:
            pass
        try:
            await client.close()
        except Exception:
            pass
