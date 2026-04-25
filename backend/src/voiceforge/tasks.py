from . import worker  # noqa: F401

import dramatiq

from .db import SessionLocal
from .services_jobs import process_job


@dramatiq.actor
def run_synthesis_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        process_job(db, job_id)
    finally:
        db.close()
