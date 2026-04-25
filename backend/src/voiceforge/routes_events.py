import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, get_db
from .services_jobs import build_live_signature, build_live_snapshot

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/snapshot")
def get_snapshot(db: Session = Depends(get_db)):
    return build_live_snapshot(db)


@router.get("/stream")
async def stream_events(request: Request):
    async def event_generator():
        last_signature = None
        while True:
            if await request.is_disconnected():
                break
            db = SessionLocal()
            try:
                signature = build_live_signature(db)
                if signature != last_signature:
                    snapshot = build_live_snapshot(db)
                    payload = snapshot.model_dump(mode="json")
                    event_id = str(int(datetime.utcnow().timestamp() * 1000))
                    yield f"id: {event_id}\nevent: snapshot\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    last_signature = signature
                else:
                    yield "event: heartbeat\ndata: {}\n\n"
            finally:
                db.close()
            await asyncio.sleep(settings.event_stream_poll_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
