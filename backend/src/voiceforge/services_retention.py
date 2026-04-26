"""Retention controls (T3.10).

Personal-use scope: delete *terminal* synthesis jobs older than N days, along
with their artifact rows and the files those artifacts point at. The preview
endpoint reports what would be deleted so the user gets a dry-run before
committing.

Out of scope: scheduled cron, per-project policies, soft-delete tombstones.
The user runs this on demand from Settings, not on a schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .enums import JobStatus
from .models import JobEvent, SynthesisArtifact, SynthesisJob
from .storage import artifact_absolute_path

TERMINAL_STATUSES = {JobStatus.succeeded.value, JobStatus.failed.value, JobStatus.canceled.value}


@dataclass
class RetentionPreview:
    cutoff_iso: str
    job_count: int
    artifact_count: int
    bytes_on_disk: int


def _cutoff(older_than_days: int) -> datetime:
    if older_than_days < 0:
        raise ValueError("older_than_days must be >= 0")
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=older_than_days)


def _candidate_jobs(db: Session, cutoff: datetime) -> list[SynthesisJob]:
    return list(
        db.scalars(
            select(SynthesisJob).where(
                SynthesisJob.status.in_(TERMINAL_STATUSES),
                SynthesisJob.finished_at.is_not(None),
                SynthesisJob.finished_at < cutoff,
            )
        ).all()
    )


def preview(db: Session, older_than_days: int) -> RetentionPreview:
    cutoff = _cutoff(older_than_days)
    jobs = _candidate_jobs(db, cutoff)
    if not jobs:
        return RetentionPreview(cutoff_iso=cutoff.isoformat(), job_count=0, artifact_count=0, bytes_on_disk=0)

    job_ids = [job.id for job in jobs]
    artifacts = list(db.scalars(select(SynthesisArtifact).where(SynthesisArtifact.job_id.in_(job_ids))).all())
    bytes_on_disk = 0
    for artifact in artifacts:
        try:
            path = artifact_absolute_path(artifact.relative_path)
            if path.exists():
                bytes_on_disk += path.stat().st_size
        except OSError:
            continue
    return RetentionPreview(
        cutoff_iso=cutoff.isoformat(),
        job_count=len(jobs),
        artifact_count=len(artifacts),
        bytes_on_disk=bytes_on_disk,
    )


def purge(db: Session, older_than_days: int) -> RetentionPreview:
    cutoff = _cutoff(older_than_days)
    jobs = _candidate_jobs(db, cutoff)
    if not jobs:
        return RetentionPreview(cutoff_iso=cutoff.isoformat(), job_count=0, artifact_count=0, bytes_on_disk=0)

    job_ids = [job.id for job in jobs]
    artifacts = list(db.scalars(select(SynthesisArtifact).where(SynthesisArtifact.job_id.in_(job_ids))).all())

    bytes_freed = 0
    for artifact in artifacts:
        try:
            path = artifact_absolute_path(artifact.relative_path)
            if path.exists():
                bytes_freed += path.stat().st_size
                path.unlink()
        except OSError:
            continue

    db.execute(delete(JobEvent).where(JobEvent.job_id.in_(job_ids)))
    db.execute(delete(SynthesisArtifact).where(SynthesisArtifact.job_id.in_(job_ids)))
    db.execute(delete(SynthesisJob).where(SynthesisJob.id.in_(job_ids)))
    db.commit()

    return RetentionPreview(
        cutoff_iso=cutoff.isoformat(),
        job_count=len(jobs),
        artifact_count=len(artifacts),
        bytes_on_disk=bytes_freed,
    )
