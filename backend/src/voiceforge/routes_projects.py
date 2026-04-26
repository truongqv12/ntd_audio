from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Project
from .schemas import CreateProjectRequest, ProjectResponse, ProjectsResponse, UpdateProjectRequest
from .services_project_export import build_export_zip
from .services_projects import create_project, get_project, list_projects, update_project
from .storage import artifact_absolute_path

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectsResponse)
def get_projects(db: Session = Depends(get_db)) -> ProjectsResponse:
    return list_projects(db)


@router.get("/{project_key}", response_model=ProjectResponse)
def get_project_route(project_key: str, db: Session = Depends(get_db)) -> ProjectResponse:
    project = get_project(db, project_key)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse)
def create_project_route(payload: CreateProjectRequest, db: Session = Depends(get_db)) -> ProjectResponse:
    try:
        return create_project(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{project_key}", response_model=ProjectResponse)
def update_project_route(
    project_key: str, payload: UpdateProjectRequest, db: Session = Depends(get_db)
) -> ProjectResponse:
    project = update_project(db, project_key, payload)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_key}/export.zip")
def download_project_export(project_key: str, db: Session = Depends(get_db)) -> Response:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    body = build_export_zip(db, project)
    return Response(
        content=body,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{project_key}.zip"'},
    )


@router.get("/{project_key}/merged-artifact")
def download_merged_project_artifact(project_key: str, path: str = Query(...)):
    artifact_path = artifact_absolute_path(path)
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Merged artifact not found")
    media_type = "audio/mpeg" if artifact_path.suffix == ".mp3" else "audio/wav"
    return FileResponse(artifact_path, media_type=media_type, filename=Path(artifact_path).name)
