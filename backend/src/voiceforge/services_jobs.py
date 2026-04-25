from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .enums import JobStatus
from .models import (
    GenerationCache,
    JobEvent,
    Project,
    ProjectScriptRow,
    SynthesisArtifact,
    SynthesisJob,
    VoiceCatalogEntry,
)
from .provider_registry import get_provider
from .schemas import (
    ArtifactResponse,
    CreateJobRequest,
    JobEventResponse,
    JobResponse,
    JobsResponse,
    LiveSnapshotResponse,
)
from .services_app_settings import apply_provider_settings
from .services_projects import ensure_project, list_projects
from .storage import artifact_absolute_path, write_artifact

logger = logging.getLogger(__name__)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_params(params: dict) -> str:
    return hashlib.sha256(str(sorted(params.items())).encode("utf-8")).hexdigest()


def _build_cache_key(
    provider_key: str, provider_voice_id: str, source_text: str, output_format: str, params: dict
) -> str:
    joined = f"{provider_key}|{provider_voice_id}|{output_format}|{_hash_text(source_text)}|{_hash_params(params)}"
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def create_job(db: Session, payload: CreateJobRequest) -> JobResponse:
    project = ensure_project(db, payload.project_key or "default")
    voice_entry = db.scalar(
        select(VoiceCatalogEntry).where(
            VoiceCatalogEntry.provider_key == payload.provider_key,
            VoiceCatalogEntry.provider_voice_id == payload.provider_voice_id,
        )
    )
    cache_key = _build_cache_key(
        payload.provider_key, payload.provider_voice_id, payload.source_text, payload.output_format, payload.params
    )
    job = SynthesisJob(
        project_id=project.id,
        provider_key=payload.provider_key,
        provider_voice_id=payload.provider_voice_id,
        voice_catalog_entry_id=voice_entry.id if voice_entry else None,
        status=JobStatus.queued.value,
        source_text=payload.source_text,
        output_format=payload.output_format,
        request_payload=payload.model_dump(),
        normalized_params=payload.params,
        cache_key=cache_key,
    )
    db.add(job)
    db.flush()
    db.add(
        JobEvent(job_id=job.id, event_type="queued", message="Job queued", payload={"project_key": project.project_key})
    )
    db.commit()
    db.refresh(job)
    logger.info(
        "job_created job_id=%s project=%s provider=%s voice=%s",
        job.id,
        project.project_key,
        job.provider_key,
        job.provider_voice_id,
    )
    return serialize_job(db, job)


def list_jobs(db: Session) -> JobsResponse:
    jobs = db.scalars(select(SynthesisJob).order_by(SynthesisJob.created_at.desc()).limit(50)).all()
    return JobsResponse(items=[serialize_job(db, job) for job in jobs])


def get_job(db: Session, job_id: str) -> JobResponse | None:
    job = db.scalar(select(SynthesisJob).where(SynthesisJob.id == job_id))
    if not job:
        return None
    return serialize_job(db, job)


def serialize_job(db: Session, job: SynthesisJob) -> JobResponse:
    artifact = next(iter(job.artifacts), None)
    project = db.get(Project, job.project_id)
    return JobResponse(
        id=job.id,
        project_key=project.project_key if project else "default",
        project_name=project.name if project else None,
        provider_key=job.provider_key,
        provider_voice_id=job.provider_voice_id,
        status=job.status,
        source_text=job.source_text,
        output_format=job.output_format,
        normalized_params=job.normalized_params or {},
        duration_seconds=job.duration_seconds,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        artifact=(
            ArtifactResponse(
                artifact_kind=artifact.artifact_kind,
                mime_type=artifact.mime_type,
                relative_path=artifact.relative_path,
                download_url=f"/jobs/{job.id}/artifact",
            )
            if artifact
            else None
        ),
        events=[
            JobEventResponse(
                event_type=item.event_type,
                message=item.message,
                payload=item.payload or {},
                created_at=item.created_at,
            )
            for item in sorted(job.events, key=lambda x: x.created_at)
        ],
    )


def build_live_snapshot(db: Session) -> LiveSnapshotResponse:
    jobs = db.scalars(select(SynthesisJob).order_by(SynthesisJob.created_at.desc()).limit(15)).all()
    events = db.scalars(select(JobEvent).order_by(JobEvent.created_at.desc()).limit(30)).all()
    return LiveSnapshotResponse(
        generated_at=datetime.utcnow(),
        jobs=[serialize_job(db, job) for job in jobs],
        events=[
            JobEventResponse(
                event_type=item.event_type,
                message=item.message,
                payload=item.payload or {},
                created_at=item.created_at,
            )
            for item in sorted(events, key=lambda x: x.created_at)
        ],
        project_stats=list_projects(db).items,
    )


def reap_stale_jobs(db: Session, max_runtime_seconds: int) -> int:
    """Mark jobs as failed if they've been running longer than max_runtime_seconds.

    Returns the number of jobs reaped. Used by the background reaper task to
    recover from worker crashes that leave jobs stuck in `running` state.
    """
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(seconds=max_runtime_seconds)
    stmt = select(SynthesisJob).where(
        SynthesisJob.status == JobStatus.running.value,
        SynthesisJob.started_at.isnot(None),
        SynthesisJob.started_at < cutoff,
    )
    stale_jobs = db.scalars(stmt).all()
    if not stale_jobs:
        return 0
    now = datetime.utcnow()
    for job in stale_jobs:
        job.status = JobStatus.failed.value
        job.error_message = f"stale job — exceeded {max_runtime_seconds}s runtime, reaped"
        job.finished_at = now
        db.add(
            JobEvent(
                job_id=job.id,
                event_type="reaped",
                message="Job reaped after exceeding max runtime",
                payload={"max_runtime_seconds": max_runtime_seconds},
            )
        )
        if job.project_script_row_id:
            row = db.get(ProjectScriptRow, job.project_script_row_id)
            if row:
                row.status = JobStatus.failed.value
                row.error_message = job.error_message
                row.updated_at = now
    db.commit()
    logger.warning("reaped_stale_jobs count=%s max_runtime_seconds=%s", len(stale_jobs), max_runtime_seconds)
    return len(stale_jobs)


def build_live_signature(db: Session) -> str:
    latest_job = db.execute(
        select(func.count(SynthesisJob.id), func.max(SynthesisJob.created_at), func.max(SynthesisJob.finished_at))
    ).one()
    latest_event = db.execute(select(func.count(JobEvent.id), func.max(JobEvent.created_at))).one()
    latest_project = db.execute(select(func.count(Project.id), func.max(Project.updated_at))).one()
    raw = "|".join(
        [
            str(latest_job[0] or 0),
            str(latest_job[1] or ""),
            str(latest_job[2] or ""),
            str(latest_event[0] or 0),
            str(latest_event[1] or ""),
            str(latest_project[0] or 0),
            str(latest_project[1] or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def process_job(db: Session, job_id: str) -> None:
    job = db.scalar(select(SynthesisJob).where(SynthesisJob.id == job_id))
    if not job:
        raise RuntimeError(f"Job not found: {job_id}")
    apply_provider_settings(db)
    provider = get_provider(job.provider_key)
    job.status = JobStatus.running.value
    job.started_at = datetime.utcnow()
    db.add(JobEvent(job_id=job.id, event_type="started", message="Synthesis started", payload={}))
    db.commit()
    logger.info("job_started job_id=%s provider=%s voice=%s", job.id, job.provider_key, job.provider_voice_id)

    existing_cache = db.scalar(select(GenerationCache).where(GenerationCache.cache_key == job.cache_key))
    if existing_cache:
        artifact = SynthesisArtifact(
            job_id=job.id,
            artifact_kind="audio",
            storage_backend="local",
            relative_path=existing_cache.relative_path,
            mime_type=existing_cache.mime_type,
            file_size_bytes=existing_cache.file_size_bytes,
            sha256_hex=existing_cache.sha256_hex,
        )
        job.status = JobStatus.succeeded.value
        job.finished_at = datetime.utcnow()
        if job.project_script_row_id:
            row = db.get(ProjectScriptRow, job.project_script_row_id)
            if row:
                row.status = JobStatus.succeeded.value
                row.last_job_id = job.id
                row.last_artifact_relative_path = existing_cache.relative_path
                row.duration_seconds = job.duration_seconds
                row.error_message = None
                row.updated_at = datetime.utcnow()
        db.add(artifact)
        db.add(JobEvent(job_id=job.id, event_type="cache_hit", message="Reused cached artifact", payload={}))
        db.commit()
        logger.info("job_cache_hit job_id=%s", job.id)
        return

    try:
        result = provider.synthesize(
            text=job.source_text,
            voice_id=job.provider_voice_id,
            output_format=job.output_format,
            params=job.normalized_params or {},
        )
        relative_path, file_size, sha256_hex = write_artifact(
            provider_key=job.provider_key,
            suffix=result.file_extension,
            content=result.audio_bytes,
        )
        artifact = SynthesisArtifact(
            job_id=job.id,
            artifact_kind="audio",
            storage_backend="local",
            relative_path=relative_path,
            mime_type=result.mime_type,
            file_size_bytes=file_size,
            sha256_hex=sha256_hex,
        )
        cache_row = GenerationCache(
            cache_key=job.cache_key,
            provider_key=job.provider_key,
            provider_voice_id=job.provider_voice_id,
            text_hash=_hash_text(job.source_text),
            params_hash=_hash_params(job.normalized_params or {}),
            relative_path=relative_path,
            mime_type=result.mime_type,
            file_size_bytes=file_size,
            sha256_hex=sha256_hex,
        )
        job.duration_seconds = result.duration_seconds
        job.status = JobStatus.succeeded.value
        job.finished_at = datetime.utcnow()
        if job.project_script_row_id:
            row = db.get(ProjectScriptRow, job.project_script_row_id)
            if row:
                row.status = JobStatus.succeeded.value
                row.last_job_id = job.id
                row.last_artifact_relative_path = relative_path
                row.duration_seconds = result.duration_seconds
                row.error_message = None
                row.updated_at = datetime.utcnow()
        db.add(artifact)
        db.add(cache_row)
        db.add(
            JobEvent(
                job_id=job.id, event_type="completed", message="Synthesis completed", payload=result.provider_metadata
            )
        )
        db.commit()
        logger.info(
            "job_completed job_id=%s provider=%s artifact=%s size=%s",
            job.id,
            job.provider_key,
            relative_path,
            file_size,
        )
    except Exception as exc:
        job.status = JobStatus.failed.value
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()
        if job.project_script_row_id:
            row = db.get(ProjectScriptRow, job.project_script_row_id)
            if row:
                row.status = JobStatus.failed.value
                row.last_job_id = job.id
                row.error_message = str(exc)
                row.updated_at = datetime.utcnow()
        db.add(JobEvent(job_id=job.id, event_type="failed", message=str(exc), payload={}))
        db.commit()
        logger.exception("job_failed job_id=%s provider=%s", job.id, job.provider_key)
        raise


def artifact_path_for_job(db: Session, job_id: str) -> Path | None:
    job = db.scalar(select(SynthesisJob).where(SynthesisJob.id == job_id))
    if not job or not job.artifacts:
        return None
    return artifact_absolute_path(job.artifacts[0].relative_path)
