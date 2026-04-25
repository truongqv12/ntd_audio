"""Cancel + retry + filtered listing for SynthesisJob (E3.1, E3.2)."""

from datetime import datetime, timedelta

from voiceforge.enums import JobStatus
from voiceforge.models import Project, SynthesisJob
from voiceforge.services_jobs import cancel_job, list_jobs, retry_job


def _project(db, key: str = "p1") -> Project:
    project = Project(project_key=key, name=key)
    db.add(project)
    db.flush()
    return project


def _job(db, *, project: Project, status: str, provider: str = "voicevox", text: str = "hi") -> SynthesisJob:
    job = SynthesisJob(
        project_id=project.id,
        provider_key=provider,
        provider_voice_id="0",
        source_text=text,
        cache_key=f"k-{datetime.utcnow().timestamp()}-{text}",
        output_format="wav",
        status=status,
        started_at=datetime.utcnow() - timedelta(seconds=5),
    )
    db.add(job)
    db.commit()
    return job


def test_cancel_queued_job_marks_canceled(db_session):
    project = _project(db_session)
    job = _job(db_session, project=project, status=JobStatus.queued.value)
    response = cancel_job(db_session, job.id)
    assert response is not None
    assert response.status == JobStatus.canceled.value
    db_session.refresh(job)
    assert job.finished_at is not None


def test_cancel_terminal_job_is_idempotent(db_session):
    project = _project(db_session)
    job = _job(db_session, project=project, status=JobStatus.succeeded.value)
    response = cancel_job(db_session, job.id)
    assert response is not None
    assert response.status == JobStatus.succeeded.value


def test_retry_failed_job_creates_new_queued_job(db_session):
    project = _project(db_session)
    original = _job(db_session, project=project, status=JobStatus.failed.value)
    response = retry_job(db_session, original.id)
    assert response is not None
    assert response.status == JobStatus.queued.value
    assert response.id != original.id


def test_retry_running_job_is_rejected_softly(db_session):
    project = _project(db_session)
    original = _job(db_session, project=project, status=JobStatus.running.value)
    response = retry_job(db_session, original.id)
    assert response is not None
    assert response.status == JobStatus.running.value
    assert response.id == original.id


def test_list_jobs_paginates_and_filters(db_session):
    project_a = _project(db_session, "alpha")
    project_b = _project(db_session, "beta")
    for i in range(3):
        _job(db_session, project=project_a, status=JobStatus.succeeded.value, text=f"alpha-{i}")
    for i in range(2):
        _job(db_session, project=project_b, status=JobStatus.failed.value, provider="piper", text=f"beta-{i}")

    everything = list_jobs(db_session)
    assert everything.total == 5
    assert len(everything.items) == 5

    paged = list_jobs(db_session, limit=2, offset=0)
    assert paged.total == 5
    assert len(paged.items) == 2

    failed_only = list_jobs(db_session, status=JobStatus.failed.value)
    assert failed_only.total == 2
    assert all(item.status == JobStatus.failed.value for item in failed_only.items)

    piper_only = list_jobs(db_session, provider_key="piper")
    assert piper_only.total == 2

    project_filter = list_jobs(db_session, project_key="alpha")
    assert project_filter.total == 3

    text_search = list_jobs(db_session, q="beta-1")
    assert text_search.total == 1
    assert text_search.items[0].source_text == "beta-1"
