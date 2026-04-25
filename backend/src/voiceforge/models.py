from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    default_provider_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_output_format: Mapped[str] = mapped_column(String(20), default="mp3", nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    jobs: Mapped[list["SynthesisJob"]] = relationship(back_populates="project")
    script_rows: Mapped[list["ProjectScriptRow"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class VoiceCatalogEntry(Base):
    __tablename__ = "voice_catalog_entries"
    __table_args__ = (
        UniqueConstraint("provider_key", "provider_voice_id", name="uq_voice_catalog_provider_voice"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_key: Mapped[str] = mapped_column(String(50), index=True)
    provider_label: Mapped[str] = mapped_column(String(120))
    provider_category: Mapped[str] = mapped_column(String(40))
    provider_voice_id: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255), index=True)
    locale: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    gender: Mapped[str | None] = mapped_column(String(40), nullable=True)
    voice_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    accent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    age: Mapped[str | None] = mapped_column(String(40), nullable=True)
    styles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preview_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    provider_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    jobs: Mapped[list["SynthesisJob"]] = relationship(back_populates="voice_entry")


class SynthesisJob(Base):
    __tablename__ = "synthesis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    external_job_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    provider_key: Mapped[str] = mapped_column(String(50), index=True)
    provider_voice_id: Mapped[str] = mapped_column(String(255), index=True)
    voice_catalog_entry_id: Mapped[str | None] = mapped_column(ForeignKey("voice_catalog_entries.id"), nullable=True)
    project_script_row_id: Mapped[str | None] = mapped_column(ForeignKey("project_script_rows.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), index=True, default="queued")
    source_text: Mapped[str] = mapped_column(Text())
    input_format: Mapped[str] = mapped_column(String(20), default="plain_text")
    output_format: Mapped[str] = mapped_column(String(20), default="mp3")
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    normalized_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cache_key: Mapped[str] = mapped_column(String(128), index=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="jobs")
    script_row: Mapped["ProjectScriptRow | None"] = relationship(back_populates="jobs")
    voice_entry: Mapped["VoiceCatalogEntry | None"] = relationship(back_populates="jobs")
    artifacts: Mapped[list["SynthesisArtifact"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    events: Mapped[list["JobEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class ProjectScriptRow(Base):
    __tablename__ = "project_script_rows"
    __table_args__ = (UniqueConstraint("project_id", "row_index", name="uq_project_script_rows_project_row"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_text: Mapped[str] = mapped_column(Text(), nullable=False)
    provider_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_voice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    join_to_master: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    last_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    last_artifact_relative_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="script_rows")
    jobs: Mapped[list["SynthesisJob"]] = relationship(back_populates="script_row")


class SynthesisArtifact(Base):
    __tablename__ = "synthesis_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("synthesis_jobs.id"), index=True)
    artifact_kind: Mapped[str] = mapped_column(String(40), default="audio")
    storage_backend: Mapped[str] = mapped_column(String(40), default="local")
    relative_path: Mapped[str] = mapped_column(Text())
    mime_type: Mapped[str] = mapped_column(String(120), default="audio/mpeg")
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_hex: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job: Mapped["SynthesisJob"] = relationship(back_populates="artifacts")


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("synthesis_jobs.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    message: Mapped[str] = mapped_column(Text())
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job: Mapped["SynthesisJob"] = relationship(back_populates="events")


class GenerationCache(Base):
    __tablename__ = "generation_cache"
    __table_args__ = (UniqueConstraint("cache_key", name="uq_generation_cache_cache_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cache_key: Mapped[str] = mapped_column(String(128), index=True)
    provider_key: Mapped[str] = mapped_column(String(50), index=True)
    provider_voice_id: Mapped[str] = mapped_column(String(255), index=True)
    text_hash: Mapped[str] = mapped_column(String(64), index=True)
    params_hash: Mapped[str] = mapped_column(String(64), index=True)
    relative_path: Mapped[str] = mapped_column(Text())
    mime_type: Mapped[str] = mapped_column(String(120), default="audio/mpeg")
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_hex: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"
    __table_args__ = (UniqueConstraint("namespace", "key", name="uq_app_settings_namespace_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    namespace: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
