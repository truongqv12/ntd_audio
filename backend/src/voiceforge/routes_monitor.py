from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import LogSourceResponse, LogTailResponse, MonitorStatusResponse
from .services_monitor import build_monitor_status, list_log_sources, read_log_tail

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/status", response_model=MonitorStatusResponse)
def get_monitor_status(db: Session = Depends(get_db)) -> MonitorStatusResponse:
    return build_monitor_status(db)


@router.get("/log-sources", response_model=list[LogSourceResponse])
def get_monitor_log_sources() -> list[LogSourceResponse]:
    return list_log_sources()


@router.get("/logs", response_model=LogTailResponse)
def get_monitor_logs(
    source: str = Query(default="api"), limit: int = Query(default=200, ge=20, le=1000)
) -> LogTailResponse:
    return read_log_tail(source_key=source, limit=limit)
