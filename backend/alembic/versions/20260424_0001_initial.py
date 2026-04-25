"""initial schema

Revision ID: 20260424_0001
Revises: None
Create Date: 2026-04-24 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260424_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("default_provider_key", sa.String(length=50), nullable=True),
        sa.Column("default_output_format", sa.String(length=20), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_projects_project_key", "projects", ["project_key"], unique=True)
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "voice_catalog_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider_key", sa.String(length=50), nullable=False),
        sa.Column("provider_label", sa.String(length=120), nullable=False),
        sa.Column("provider_category", sa.String(length=40), nullable=False),
        sa.Column("provider_voice_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=40), nullable=True),
        sa.Column("language", sa.String(length=80), nullable=True),
        sa.Column("gender", sa.String(length=40), nullable=True),
        sa.Column("voice_type", sa.String(length=60), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("accent", sa.String(length=80), nullable=True),
        sa.Column("age", sa.String(length=40), nullable=True),
        sa.Column("styles", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("preview_url", sa.Text(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("provider_metadata", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider_key", "provider_voice_id", name="uq_voice_catalog_provider_voice"),
    )
    op.create_index("ix_voice_catalog_entries_provider_key", "voice_catalog_entries", ["provider_key"])
    op.create_index("ix_voice_catalog_entries_display_name", "voice_catalog_entries", ["display_name"])
    op.create_index("ix_voice_catalog_entries_locale", "voice_catalog_entries", ["locale"])
    op.create_index("ix_voice_catalog_entries_language", "voice_catalog_entries", ["language"])

    op.create_table(
        "synthesis_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("external_job_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("provider_key", sa.String(length=50), nullable=False),
        sa.Column("provider_voice_id", sa.String(length=255), nullable=False),
        sa.Column("voice_catalog_entry_id", sa.String(length=36), sa.ForeignKey("voice_catalog_entries.id"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("input_format", sa.String(length=20), nullable=False),
        sa.Column("output_format", sa.String(length=20), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("normalized_params", sa.JSON(), nullable=False),
        sa.Column("cache_key", sa.String(length=128), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_synthesis_jobs_external_job_id", "synthesis_jobs", ["external_job_id"], unique=True)
    op.create_index("ix_synthesis_jobs_project_id", "synthesis_jobs", ["project_id"])
    op.create_index("ix_synthesis_jobs_provider_key", "synthesis_jobs", ["provider_key"])
    op.create_index("ix_synthesis_jobs_provider_voice_id", "synthesis_jobs", ["provider_voice_id"])
    op.create_index("ix_synthesis_jobs_status", "synthesis_jobs", ["status"])
    op.create_index("ix_synthesis_jobs_cache_key", "synthesis_jobs", ["cache_key"])

    op.create_table(
        "synthesis_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("synthesis_jobs.id"), nullable=False),
        sa.Column("artifact_kind", sa.String(length=40), nullable=False),
        sa.Column("storage_backend", sa.String(length=40), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256_hex", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_synthesis_artifacts_job_id", "synthesis_artifacts", ["job_id"])
    op.create_index("ix_synthesis_artifacts_sha256_hex", "synthesis_artifacts", ["sha256_hex"])

    op.create_table(
        "job_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("synthesis_jobs.id"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])
    op.create_index("ix_job_events_event_type", "job_events", ["event_type"])

    op.create_table(
        "generation_cache",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("cache_key", sa.String(length=128), nullable=False),
        sa.Column("provider_key", sa.String(length=50), nullable=False),
        sa.Column("provider_voice_id", sa.String(length=255), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column("params_hash", sa.String(length=64), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256_hex", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("cache_key", name="uq_generation_cache_cache_key"),
    )
    op.create_index("ix_generation_cache_cache_key", "generation_cache", ["cache_key"])
    op.create_index("ix_generation_cache_provider_key", "generation_cache", ["provider_key"])
    op.create_index("ix_generation_cache_provider_voice_id", "generation_cache", ["provider_voice_id"])
    op.create_index("ix_generation_cache_text_hash", "generation_cache", ["text_hash"])
    op.create_index("ix_generation_cache_params_hash", "generation_cache", ["params_hash"])


def downgrade() -> None:
    op.drop_table("generation_cache")
    op.drop_table("job_events")
    op.drop_table("synthesis_artifacts")
    op.drop_table("synthesis_jobs")
    op.drop_table("voice_catalog_entries")
    op.drop_table("projects")
