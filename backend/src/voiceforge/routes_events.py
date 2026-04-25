import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, get_db
from .events_bus import subscribe_jobs_changed
from .services_jobs import build_live_signature, build_live_snapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


@router.get("/snapshot")
def get_snapshot(db: Session = Depends(get_db)):
    return build_live_snapshot(db)


def _emit_snapshot() -> str:
    db = SessionLocal()
    try:
        snapshot = build_live_snapshot(db)
        payload = snapshot.model_dump(mode="json")
    finally:
        db.close()
    event_id = str(int(datetime.utcnow().timestamp() * 1000))
    return f"id: {event_id}\nevent: snapshot\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _current_signature() -> str:
    db = SessionLocal()
    try:
        return build_live_signature(db)
    finally:
        db.close()


@router.get("/stream")
async def stream_events(request: Request):
    """SSE stream backed by Redis pub/sub.

    On connect we send an initial snapshot, then push a fresh snapshot every
    time a notification arrives on the events bus. Heartbeats every
    ``EVENT_STREAM_HEARTBEAT_SECONDS`` keep proxies from closing the connection
    and act as a fallback when Redis is unavailable.
    """

    async def event_generator():
        # initial snapshot so reconnecting clients get state immediately
        yield _emit_snapshot()
        last_signature = _current_signature()
        heartbeat = float(getattr(settings, "event_stream_heartbeat_seconds", 15.0))

        async for message in subscribe_jobs_changed(heartbeat_seconds=heartbeat):
            if await request.is_disconnected():
                return
            reason = message.get("reason", "heartbeat")
            if reason == "heartbeat":
                # Cheap signature recheck so we still update if Redis is down
                # or a publisher missed a transition.
                signature = _current_signature()
                if signature != last_signature:
                    yield _emit_snapshot()
                    last_signature = signature
                else:
                    yield "event: heartbeat\ndata: {}\n\n"
                continue
            yield _emit_snapshot()
            last_signature = _current_signature()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
