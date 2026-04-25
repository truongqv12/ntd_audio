from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import CreateJobRequest, JobResponse, JobsResponse
from .services_jobs import artifact_path_for_job, create_job, get_job, list_jobs
from .tasks import run_synthesis_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobsResponse)
def get_jobs(db: Session = Depends(get_db)) -> JobsResponse:
    return list_jobs(db)


@router.get("/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: str, db: Session = Depends(get_db)) -> JobResponse:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=JobResponse)
def create_job_route(payload: CreateJobRequest, db: Session = Depends(get_db)) -> JobResponse:
    job = create_job(db, payload)
    run_synthesis_job.send(job.id)
    return job


@router.get("/{job_id}/artifact")
def download_artifact(job_id: str, db: Session = Depends(get_db)):
    path = artifact_path_for_job(db, job_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    media_type = "audio/mpeg" if path.suffix == ".mp3" else "audio/wav"
    return FileResponse(path, media_type=media_type, filename=path.name)
