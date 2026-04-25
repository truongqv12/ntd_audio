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


def _snapshot_with_signature() -> tuple[str, str]:
    """Return (sse_event, signature) computed in a single DB session.

    Reading signature *before* the snapshot in the same session guarantees
    ``signature`` is ≤ the snapshot data — never ahead. If we did the reverse,
    or used two sessions, a commit landing between the two reads could leave
    ``last_signature`` pointing past data the client already received and the
    update would be silently swallowed on the next compare.
    """
    db = SessionLocal()
    try:
        signature = build_live_signature(db)
        snapshot = build_live_snapshot(db)
        payload = snapshot.model_dump(mode="json")
    finally:
        db.close()
    event_id = str(int(datetime.utcnow().timestamp() * 1000))
    sse = f"id: {event_id}\nevent: snapshot\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
    return sse, signature


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
        sse, last_signature = _snapshot_with_signature()
        yield sse
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
                    sse, last_signature = _snapshot_with_signature()
                    yield sse
                else:
                    yield "event: heartbeat\ndata: {}\n\n"
                continue
            sse, last_signature = _snapshot_with_signature()
            yield sse

    return StreamingResponse(event_generator(), media_type="text/event-stream")
