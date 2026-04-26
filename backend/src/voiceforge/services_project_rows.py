from __future__ import annotations

import io
import re
import subprocess
import tempfile
import zipfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .models import Project, ProjectScriptRow, SynthesisJob, VoiceCatalogEntry
from .schemas import (
    BulkImportResponse,
    JobResponse,
    ProjectBatchQueueResponse,
    ProjectMergeResponse,
    ProjectRowsResponse,
    ProjectScriptRowResponse,
    QueueProjectRowsRequest,
    UpsertProjectRowsRequest,
)
from .services_bulk_import import ParsedRow
from .services_jobs import _build_cache_key, serialize_job
from .services_projects import ensure_project
from .storage import artifact_absolute_path, write_artifact


def _serialize_row(project: Project, row: ProjectScriptRow) -> ProjectScriptRowResponse:
    download_url = None
    if row.last_artifact_relative_path:
        download_url = f"/projects/{project.project_key}/rows/{row.id}/artifact"
    return ProjectScriptRowResponse(
        id=row.id,
        project_key=project.project_key,
        row_index=row.row_index,
        title=row.title,
        source_text=row.source_text,
        speaker_label=row.speaker_label,
        provider_key=row.provider_key,
        provider_voice_id=row.provider_voice_id,
        output_format=row.output_format,
        params=row.params or {},
        is_enabled=row.is_enabled,
        join_to_master=row.join_to_master,
        status=row.status,
        last_job_id=row.last_job_id,
        last_artifact_download_url=download_url,
        duration_seconds=row.duration_seconds,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_project_rows(db: Session, project_key: str) -> ProjectRowsResponse | None:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        return None
    rows = db.scalars(
        select(ProjectScriptRow)
        .where(ProjectScriptRow.project_id == project.id)
        .order_by(ProjectScriptRow.row_index.asc())
    ).all()
    return ProjectRowsResponse(items=[_serialize_row(project, row) for row in rows])


def replace_project_rows(db: Session, project_key: str, payload: UpsertProjectRowsRequest) -> ProjectRowsResponse:
    project = ensure_project(db, project_key)
    db.execute(delete(ProjectScriptRow).where(ProjectScriptRow.project_id == project.id))
    for item in payload.rows:
        row = ProjectScriptRow(
            project_id=project.id,
            row_index=item.row_index,
            title=item.title,
            source_text=item.source_text,
            speaker_label=item.speaker_label,
            provider_key=item.provider_key,
            provider_voice_id=item.provider_voice_id,
            output_format=item.output_format,
            params=item.params,
            is_enabled=item.is_enabled,
            join_to_master=item.join_to_master,
            status="draft",
        )
        db.add(row)
    db.commit()
    return list_project_rows(db, project_key)  # type: ignore[return-value]


def queue_project_rows(
    db: Session, project_key: str, payload: QueueProjectRowsRequest
) -> ProjectBatchQueueResponse | None:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        return None
    stmt = (
        select(ProjectScriptRow)
        .where(ProjectScriptRow.project_id == project.id, ProjectScriptRow.is_enabled.is_(True))
        .order_by(ProjectScriptRow.row_index.asc())
    )
    rows = db.scalars(stmt).all()
    if payload.row_ids:
        allowed = set(payload.row_ids)
        rows = [row for row in rows if row.id in allowed]

    created: list[JobResponse] = []
    for row in rows:
        provider_key = row.provider_key or project.default_provider_key
        provider_voice_id = row.provider_voice_id
        output_format = row.output_format or project.default_output_format
        if not provider_key or not provider_voice_id:
            row.status = "failed"
            row.error_message = "Missing provider or voice selection"
            row.updated_at = datetime.utcnow()
            continue
        voice_entry = db.scalar(
            select(VoiceCatalogEntry).where(
                VoiceCatalogEntry.provider_key == provider_key,
                VoiceCatalogEntry.provider_voice_id == provider_voice_id,
            )
        )
        params = row.params or {}
        cache_key = _build_cache_key(provider_key, provider_voice_id, row.source_text, output_format, params)
        job = SynthesisJob(
            project_id=project.id,
            provider_key=provider_key,
            provider_voice_id=provider_voice_id,
            voice_catalog_entry_id=voice_entry.id if voice_entry else None,
            project_script_row_id=row.id,
            status="queued",
            source_text=row.source_text,
            output_format=output_format,
            request_payload={
                "project_key": project.project_key,
                "provider_key": provider_key,
                "provider_voice_id": provider_voice_id,
                "source_text": row.source_text,
                "output_format": output_format,
                "params": params,
                "project_script_row_id": row.id,
            },
            normalized_params=params,
            cache_key=cache_key,
        )
        db.add(job)
        db.flush()
        row.status = "queued"
        row.last_job_id = job.id
        row.error_message = None
        row.updated_at = datetime.utcnow()
        created.append(serialize_job(db, job))
    db.commit()
    return ProjectBatchQueueResponse(queued_jobs=created, merge_requested=payload.merge_outputs)


def project_row_artifact_path(db: Session, project_key: str, row_id: str) -> Path | None:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        return None
    row = db.scalar(
        select(ProjectScriptRow).where(ProjectScriptRow.project_id == project.id, ProjectScriptRow.id == row_id)
    )
    if not row or not row.last_artifact_relative_path:
        return None
    return artifact_absolute_path(row.last_artifact_relative_path)


def merge_project_rows(db: Session, project_key: str, payload: QueueProjectRowsRequest) -> ProjectMergeResponse | None:
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        return None
    rows = db.scalars(
        select(ProjectScriptRow)
        .where(
            ProjectScriptRow.project_id == project.id,
            ProjectScriptRow.is_enabled.is_(True),
            ProjectScriptRow.join_to_master.is_(True),
            ProjectScriptRow.last_artifact_relative_path.is_not(None),
        )
        .order_by(ProjectScriptRow.row_index.asc())
    ).all()
    if payload.row_ids:
        allowed = set(payload.row_ids)
        rows = [row for row in rows if row.id in allowed]
    if not rows:
        raise RuntimeError("No completed project rows available to merge")

    output_format = (payload.merge_output_format or "wav").lower()
    silence_ms = max(0, payload.merge_silence_ms)
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = Path(tmpdir) / "concat.txt"
        merged_path = Path(tmpdir) / f"merged.{output_format}"
        normalized_files: list[Path] = []
        for idx, row in enumerate(rows):
            source = artifact_absolute_path(row.last_artifact_relative_path)
            intermediate = Path(tmpdir) / f"row_{idx}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(source), str(intermediate)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            normalized_files.append(intermediate)
            if silence_ms > 0 and idx < len(rows) - 1:
                silence = Path(tmpdir) / f"silence_{idx}.wav"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=r=24000:cl=mono",
                        "-t",
                        str(silence_ms / 1000),
                        str(silence),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                normalized_files.append(silence)
        manifest.write_text("\n".join([f"file '{item}'" for item in normalized_files]), encoding="utf-8")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest), str(merged_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        relative_path, _, _ = write_artifact(
            provider_key="project-merge", suffix=output_format, content=merged_path.read_bytes()
        )
    return ProjectMergeResponse(
        project_key=project.project_key,
        merged_count=len(rows),
        output_format=output_format,
        download_url=f"/projects/{project.project_key}/merged-artifact?path={quote(relative_path, safe='')}",
    )


_SLUG_RE = re.compile(r"[^A-Za-z0-9]+")


def _slugify(text: str, *, max_len: int = 40) -> str:
    cleaned = _SLUG_RE.sub("-", text).strip("-").lower()
    if not cleaned:
        cleaned = "row"
    return cleaned[:max_len].rstrip("-") or "row"


def bulk_import_rows(
    db: Session,
    project_key: str,
    parsed_rows: list[ParsedRow],
    *,
    default_provider_key: str | None = None,
    default_voice_id: str | None = None,
) -> tuple[Project, list[ProjectScriptRow]]:
    """Append parsed rows to a project. Caller is responsible for triggering jobs."""
    project = ensure_project(db, project_key)
    next_index = (
        db.scalar(
            select(func.coalesce(func.max(ProjectScriptRow.row_index), -1)).where(
                ProjectScriptRow.project_id == project.id
            )
        )
        or -1
    ) + 1

    inserted: list[ProjectScriptRow] = []
    for offset, parsed in enumerate(parsed_rows):
        row = ProjectScriptRow(
            project_id=project.id,
            row_index=next_index + offset,
            title=parsed.title,
            source_text=parsed.text,
            provider_key=default_provider_key,
            provider_voice_id=parsed.provider_voice_id or default_voice_id,
            output_format=None,
            params={},
            is_enabled=True,
            join_to_master=True,
            status="draft",
        )
        db.add(row)
        inserted.append(row)
    db.commit()
    for row in inserted:
        db.refresh(row)
    return project, inserted


def bulk_import_to_response(project: Project, rows: list[ProjectScriptRow]) -> BulkImportResponse:
    return BulkImportResponse(
        project_key=project.project_key,
        inserted=len(rows),
        rows=[_serialize_row(project, row) for row in rows],
    )


def stream_artifacts_zip(
    db: Session, project_key: str, *, status_filter: str | None = "succeeded"
) -> Iterator[bytes] | None:
    """Stream a zip of all artifacts for a project. Returns None if project missing."""
    project = db.scalar(select(Project).where(Project.project_key == project_key))
    if not project:
        return None

    stmt = (
        select(ProjectScriptRow)
        .where(
            ProjectScriptRow.project_id == project.id,
            ProjectScriptRow.last_artifact_relative_path.is_not(None),
        )
        .order_by(ProjectScriptRow.row_index.asc())
    )
    if status_filter:
        stmt = stmt.where(ProjectScriptRow.status == status_filter)
    rows = db.scalars(stmt).all()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for row in rows:
            assert row.last_artifact_relative_path is not None
            source = artifact_absolute_path(row.last_artifact_relative_path)
            if not source.exists():
                continue
            ext = source.suffix.lstrip(".") or "wav"
            slug = _slugify(row.source_text)
            arcname = f"{project.project_key}_{row.row_index:03d}_{slug}.{ext}"
            archive.write(source, arcname=arcname)
    buffer.seek(0)
    return iter([buffer.getvalue()])
