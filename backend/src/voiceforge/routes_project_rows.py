from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Project, ProjectScriptRow
from .schemas import (
    BulkImportResponse,
    ProjectBatchQueueResponse,
    ProjectMergeResponse,
    ProjectRowsResponse,
    QueueProjectRowsRequest,
    UpsertProjectRowsRequest,
)
from .services_bulk_import import parse_csv, parse_txt
from .services_project_rows import (
    bulk_import_rows,
    bulk_import_to_response,
    list_project_rows,
    merge_project_rows,
    project_row_artifact_path,
    queue_project_rows,
    replace_project_rows,
    stream_artifacts_zip,
)
from .services_subtitles import render as render_subtitles
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


@router.post("/bulk", response_model=BulkImportResponse)
async def bulk_import(
    project_key: str,
    file: UploadFile = File(...),
    file_format: Literal["txt", "csv"] = Form("txt", alias="format"),
    text_column: str = Form("text"),
    voice_column: str | None = Form(None),
    speaker_column: str | None = Form(None),
    title_column: str | None = Form(None),
    txt_split: Literal["line", "blank-line"] = Form("line"),
    default_provider_key: str | None = Form(None),
    default_voice_id: str | None = Form(None),
    auto_enqueue: bool = Form(False),
    db: Session = Depends(get_db),
) -> BulkImportResponse:
    raw = await file.read()
    if len(raw) > settings.bulk_import_max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds limit ({settings.bulk_import_max_bytes} bytes)",
        )
    try:
        if file_format == "txt":
            parsed = parse_txt(raw, split=txt_split)
        else:
            parsed = parse_csv(
                raw,
                text_column=text_column,
                voice_column=voice_column,
                speaker_column=speaker_column,
                title_column=title_column,
            )
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    if not parsed:
        raise HTTPException(status_code=422, detail="No usable rows were found in the upload")
    if len(parsed) > settings.bulk_import_max_rows:
        raise HTTPException(
            status_code=422,
            detail=f"Too many rows ({len(parsed)} > {settings.bulk_import_max_rows})",
        )

    project, rows = bulk_import_rows(
        db,
        project_key,
        parsed,
        default_provider_key=default_provider_key,
        default_voice_id=default_voice_id,
    )
    response = bulk_import_to_response(project, rows)

    if auto_enqueue:
        queue_response = queue_project_rows(
            db,
            project_key,
            QueueProjectRowsRequest(row_ids=[row.id for row in rows]),
        )
        if queue_response is not None:
            for job in queue_response.queued_jobs:
                run_synthesis_job.send(job.id)
            response.queued_jobs = queue_response.queued_jobs
            for row in rows:
                db.refresh(row)
            response = bulk_import_to_response(project, rows)
            response.queued_jobs = queue_response.queued_jobs
    return response


@router.get("/artifacts.zip")
def download_artifacts_zip(
    project_key: str,
    status: str | None = "succeeded",
    db: Session = Depends(get_db),
) -> StreamingResponse:
    chunks = stream_artifacts_zip(db, project_key, status_filter=status)
    if chunks is None:
        raise HTTPException(status_code=404, detail="Project not found")
    headers = {"Content-Disposition": f'attachment; filename="{project_key}-artifacts.zip"'}
    return StreamingResponse(chunks, media_type="application/zip", headers=headers)


@router.get("/subtitles")
def download_project_subtitles(
    project_key: str,
    db: Session = Depends(get_db),
    file_format: str = Query("srt", alias="format", pattern="^(srt|vtt)$"),
    silence_ms: int = Query(150, ge=0, le=10000),
    only_completed: bool = Query(True),
) -> Response:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    stmt = (
        select(ProjectScriptRow)
        .where(
            ProjectScriptRow.project_id == project.id,
            ProjectScriptRow.is_enabled.is_(True),
        )
        .order_by(ProjectScriptRow.row_index.asc())
    )
    if only_completed:
        stmt = stmt.where(ProjectScriptRow.last_artifact_relative_path.is_not(None))
    rows = list(db.scalars(stmt).all())
    if not rows:
        raise HTTPException(status_code=404, detail="No rows available for subtitles")
    body, mime = render_subtitles(rows, file_format=file_format, silence_ms=silence_ms)
    filename = f"{project_key}.{file_format}"
    return Response(
        content=body,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{row_id}/artifact")
def download_row_artifact(project_key: str, row_id: str, db: Session = Depends(get_db)):
    path = project_row_artifact_path(db, project_key, row_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    media_type = "audio/mpeg" if path.suffix == ".mp3" else "audio/wav"
    return FileResponse(path, media_type=media_type, filename=Path(path).name)
