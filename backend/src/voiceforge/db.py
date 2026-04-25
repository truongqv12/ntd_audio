import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    from . import models  # noqa: F401

    if settings.app_env in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    else:
        logger.info(
            "init_db_skipped_create_all app_env=%s reason=alembic_is_source_of_truth",
            settings.app_env,
        )
