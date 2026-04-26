"""Retention controls (T3.10)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from voiceforge.config import settings
from voiceforge.models import Project, SynthesisArtifact, SynthesisJob
from voiceforge.services_retention import preview, purge


def _project(db) -> Project:
    project = Project(project_key="p1", name="p1")
    db.add(project)
    db.flush()
    return project


def _job(db, *, project_id: str, status: str, finished_offset_days: float | None) -> SynthesisJob:
    finished = datetime.utcnow() - timedelta(days=finished_offset_days) if finished_offset_days is not None else None
    job = SynthesisJob(
        project_id=project_id,
        provider_key="fake",
        provider_voice_id="fake:1",
        status=status,
        source_text="hi",
        cache_key="x",
        finished_at=finished,
    )
    db.add(job)
    db.flush()
    return job


def _artifact(db, *, job_id: str, relpath: str, payload: bytes) -> SynthesisArtifact:
    abs_path = settings.artifact_root / relpath
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(payload)
    artifact = SynthesisArtifact(
        job_id=job_id,
        relative_path=relpath,
        file_size_bytes=len(payload),
    )
    db.add(artifact)
    db.flush()
    return artifact


@pytest.fixture()
def project(db_session) -> Project:
    return _project(db_session)


def test_preview_counts_only_old_terminal_jobs(db_session, project, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifact_root", tmp_path)
    old = _job(db_session, project_id=project.id, status="succeeded", finished_offset_days=40)
    _artifact(db_session, job_id=old.id, relpath="fake/old.wav", payload=b"OLD")
    _job(db_session, project_id=project.id, status="succeeded", finished_offset_days=5)  # too recent
    _job(db_session, project_id=project.id, status="running", finished_offset_days=None)  # active

    result = preview(db_session, older_than_days=30)
    assert result.job_count == 1
    assert result.artifact_count == 1
    assert result.bytes_on_disk == 3


def test_purge_removes_jobs_and_files(db_session, project, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifact_root", tmp_path)
    old = _job(db_session, project_id=project.id, status="succeeded", finished_offset_days=40)
    artifact_path = tmp_path / "fake" / "old.wav"
    _artifact(db_session, job_id=old.id, relpath="fake/old.wav", payload=b"PAYLOAD")
    assert artifact_path.exists()

    result = purge(db_session, older_than_days=30)
    assert result.job_count == 1
    assert not artifact_path.exists()
    assert db_session.get(SynthesisJob, old.id) is None


def test_purge_skips_when_nothing_matches(db_session, project, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifact_root", tmp_path)
    _job(db_session, project_id=project.id, status="succeeded", finished_offset_days=5)
    result = purge(db_session, older_than_days=30)
    assert result.job_count == 0
    assert result.bytes_on_disk == 0


def test_negative_window_rejected(db_session):
    with pytest.raises(ValueError):
        preview(db_session, older_than_days=-1)
