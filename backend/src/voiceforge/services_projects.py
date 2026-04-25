from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from .models import Project, SynthesisJob
from .schemas import CreateProjectRequest, ProjectResponse, ProjectsResponse, ProjectStatsResponse, UpdateProjectRequest


def _project_stats_map(db: Session) -> dict[str, ProjectStatsResponse]:
    rows = db.execute(
        select(
            SynthesisJob.project_id,
            func.count(SynthesisJob.id).label("total_jobs"),
            func.sum(case((SynthesisJob.status == "queued", 1), else_=0)).label("queued_jobs"),
            func.sum(case((SynthesisJob.status == "running", 1), else_=0)).label("running_jobs"),
            func.sum(case((SynthesisJob.status == "succeeded", 1), else_=0)).label("succeeded_jobs"),
            func.sum(case((SynthesisJob.status == "failed", 1), else_=0)).label("failed_jobs"),
            func.max(SynthesisJob.created_at).label("last_job_created_at"),
        ).group_by(SynthesisJob.project_id)
    ).all()
    result: dict[str, ProjectStatsResponse] = {}
    for row in rows:
        result[row.project_id] = ProjectStatsResponse(
            total_jobs=int(row.total_jobs or 0),
            queued_jobs=int(row.queued_jobs or 0),
            running_jobs=int(row.running_jobs or 0),
            succeeded_jobs=int(row.succeeded_jobs or 0),
            failed_jobs=int(row.failed_jobs or 0),
            last_job_created_at=row.last_job_created_at,
        )
    return result


def serialize_project(
    db: Session, project: Project, stats_map: dict[str, ProjectStatsResponse] | None = None
) -> ProjectResponse:
    stats_map = stats_map or _project_stats_map(db)
    return ProjectResponse(
        id=project.id,
        project_key=project.project_key,
        name=project.name,
        description=project.description,
        status=project.status,
        default_provider_key=project.default_provider_key,
        default_output_format=project.default_output_format,
        tags=list(project.tags or []),
        settings=project.settings or {},
        is_default=project.is_default,
        archived_at=project.archived_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        stats=stats_map.get(project.id, ProjectStatsResponse()),
    )


def ensure_project(db: Session, project_key: str = "default") -> Project:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if project:
        return project
    project = Project(
        project_key=project_key,
        name="Default Project" if project_key == "default" else project_key.replace("_", " ").title(),
        description="Default local workspace" if project_key == "default" else None,
        is_default=project_key == "default",
        tags=["default"] if project_key == "default" else [],
        settings={"ui_theme": "dark", "auto_preview": True} if project_key == "default" else {},
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session) -> ProjectsResponse:
    items = db.scalars(select(Project).order_by(Project.is_default.desc(), Project.updated_at.desc())).all()
    stats_map = _project_stats_map(db)
    return ProjectsResponse(items=[serialize_project(db, item, stats_map=stats_map) for item in items])


def get_project(db: Session, project_key: str) -> ProjectResponse | None:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        return None
    stats_map = _project_stats_map(db)
    return serialize_project(db, project, stats_map=stats_map)


def create_project(db: Session, payload: CreateProjectRequest) -> ProjectResponse:
    existing = db.scalar(select(Project).where(Project.project_key == payload.project_key))
    if existing:
        raise ValueError(f"Project already exists: {payload.project_key}")
    if payload.is_default:
        for project in db.scalars(select(Project).where(Project.is_default.is_(True))).all():
            project.is_default = False
    project = Project(
        project_key=payload.project_key,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        default_provider_key=payload.default_provider_key,
        default_output_format=payload.default_output_format,
        tags=payload.tags,
        settings=payload.settings,
        is_default=payload.is_default,
        archived_at=datetime.utcnow() if payload.status == "archived" else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_project(db, project)


def update_project(db: Session, project_key: str, payload: UpdateProjectRequest) -> ProjectResponse | None:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        return None
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default") is True:
        for item in db.scalars(select(Project).where(Project.is_default.is_(True))).all():
            item.is_default = False
    for key, value in data.items():
        setattr(project, key, value)
    if data.get("status") == "archived" and project.archived_at is None:
        project.archived_at = datetime.utcnow()
    if data.get("status") == "active":
        project.archived_at = None
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return serialize_project(db, project)
