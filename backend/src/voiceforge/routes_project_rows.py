from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import (
    ProjectBatchQueueResponse,
    ProjectMergeResponse,
    ProjectRowsResponse,
    QueueProjectRowsRequest,
    UpsertProjectRowsRequest,
)
from .services_project_rows import (
    list_project_rows,
    merge_project_rows,
    project_row_artifact_path,
    queue_project_rows,
    replace_project_rows,
)
from .tasks import run_synthesis_job

router = APIRouter(prefix="/projects/{project_key}/rows", tags=["project-rows"])


@router.get("", response_model=ProjectRowsResponse)
def get_project_rows(project_key: str, db: Session = Depends(get_db)) -> ProjectRowsResponse:
    rows = list_project_rows(db, project_key)
    if rows is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return rows


@router.put("", response_model=ProjectRowsResponse)
def put_project_rows(
    project_key: str, payload: UpsertProjectRowsRequest, db: Session = Depends(get_db)
) -> ProjectRowsResponse:
    return replace_project_rows(db, project_key, payload)


@router.post("/queue", response_model=ProjectBatchQueueResponse)
def queue_rows(
    project_key: str, payload: QueueProjectRowsRequest, db: Session = Depends(get_db)
) -> ProjectBatchQueueResponse:
    response = queue_project_rows(db, project_key, payload)
    if response is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for job in response.queued_jobs:
        run_synthesis_job.send(job.id)
    return response


@router.post("/merge", response_model=ProjectMergeResponse)
def merge_rows(
    project_key: str, payload: QueueProjectRowsRequest, db: Session = Depends(get_db)
) -> ProjectMergeResponse:
    response = merge_project_rows(db, project_key, payload)
    if response is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return response


@router.get("/{row_id}/artifact")
def download_row_artifact(project_key: str, row_id: str, db: Session = Depends(get_db)):
    path = project_row_artifact_path(db, project_key, row_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    media_type = "audio/mpeg" if path.suffix == ".mp3" else "audio/wav"
    return FileResponse(path, media_type=media_type, filename=Path(path).name)
