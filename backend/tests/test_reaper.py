from datetime import datetime, timedelta

from voiceforge.enums import JobStatus
from voiceforge.models import Project, SynthesisJob
from voiceforge.services_jobs import reap_stale_jobs


def _make_job(db, *, started_at: datetime, status: str = JobStatus.running.value) -> SynthesisJob:
    project = Project(project_key="test", name="test")
    db.add(project)
    db.flush()
    job = SynthesisJob(
        project_id=project.id,
        provider_key="voicevox",
        provider_voice_id="0",
        source_text="hello",
        cache_key="cache-test",
        output_format="wav",
        status=status,
        started_at=started_at,
    )
    db.add(job)
    db.commit()
    return job


def test_reap_marks_old_running_jobs_as_failed(db_session):
    stale_started = datetime.utcnow() - timedelta(seconds=2000)
    job = _make_job(db_session, started_at=stale_started)

    reaped = reap_stale_jobs(db_session, max_runtime_seconds=900)

    assert reaped == 1
    db_session.refresh(job)
    assert job.status == JobStatus.failed.value
    assert job.error_message is not None
    assert "stale job" in job.error_message
    assert job.finished_at is not None


def test_reap_leaves_recent_running_jobs_alone(db_session):
    fresh_started = datetime.utcnow() - timedelta(seconds=10)
    job = _make_job(db_session, started_at=fresh_started)

    reaped = reap_stale_jobs(db_session, max_runtime_seconds=900)

    assert reaped == 0
    db_session.refresh(job)
    assert job.status == JobStatus.running.value


def test_reap_ignores_finished_jobs(db_session):
    very_old = datetime.utcnow() - timedelta(seconds=99999)
    job = _make_job(db_session, started_at=very_old, status=JobStatus.succeeded.value)

    reaped = reap_stale_jobs(db_session, max_runtime_seconds=900)

    assert reaped == 0
    db_session.refresh(job)
    assert job.status == JobStatus.succeeded.value
