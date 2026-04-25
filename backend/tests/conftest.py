"""Pytest fixtures: in-memory sqlite DB shared across the test process.

We override DATABASE_URL via env BEFORE importing voiceforge, then build
all tables with Base.metadata.create_all so each test starts with a clean DB.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("APP_ENCRYPTION_KEY", "")
os.environ.setdefault("VOICE_CATALOG_REFRESH_ON_START", "false")
os.environ.setdefault("JOB_REAPER_ENABLED", "false")
os.environ.setdefault("ARTIFACT_ROOT", str(REPO_ROOT / ".tmp" / "artifacts"))
os.environ.setdefault("CACHE_ROOT", str(REPO_ROOT / ".tmp" / "cache"))
os.environ.setdefault("LOG_FILE_PATH", str(REPO_ROOT / ".tmp" / "log.log"))


@pytest.fixture()
def db_session() -> Generator:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from voiceforge import db as db_module
    from voiceforge.db import Base

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    original_engine = db_module.engine
    original_session = db_module.SessionLocal
    db_module.engine = engine
    db_module.SessionLocal = SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        db_module.engine = original_engine
        db_module.SessionLocal = original_session
