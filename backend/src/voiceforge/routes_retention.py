from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import get_db
from .services_retention import preview, purge

router = APIRouter(prefix="/admin/retention", tags=["retention"])


class PurgeRequest(BaseModel):
    older_than_days: int = Field(ge=0)
    confirm: bool = False


@router.get("/preview")
def retention_preview(
    older_than_days: int = Query(30, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    return asdict(preview(db, older_than_days))


@router.post("/purge")
def retention_purge(payload: PurgeRequest, db: Session = Depends(get_db)) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="confirm=true is required to purge")
    return asdict(purge(db, payload.older_than_days))
