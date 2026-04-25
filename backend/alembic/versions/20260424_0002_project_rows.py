"""project rows and job row linkage

Revision ID: 20260424_0002
Revises: 20260424_0001
Create Date: 2026-04-24 00:30:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260424_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_script_rows",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("provider_key", sa.String(length=50), nullable=True),
        sa.Column("provider_voice_id", sa.String(length=255), nullable=True),
        sa.Column("output_format", sa.String(length=20), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("join_to_master", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_job_id", sa.String(length=36), nullable=True),
        sa.Column("last_artifact_relative_path", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("project_id", "row_index", name="uq_project_script_rows_project_row"),
    )
    op.create_index("ix_project_script_rows_project_id", "project_script_rows", ["project_id"])
    op.create_index("ix_project_script_rows_status", "project_script_rows", ["status"])
    op.create_index("ix_project_script_rows_last_job_id", "project_script_rows", ["last_job_id"])

    op.add_column("synthesis_jobs", sa.Column("project_script_row_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(None, "synthesis_jobs", "project_script_rows", ["project_script_row_id"], ["id"])
    op.create_index("ix_synthesis_jobs_project_script_row_id", "synthesis_jobs", ["project_script_row_id"])


def downgrade() -> None:
    op.drop_index("ix_synthesis_jobs_project_script_row_id", table_name="synthesis_jobs")
    op.drop_constraint(None, "synthesis_jobs", type_="foreignkey")
    op.drop_column("synthesis_jobs", "project_script_row_id")

    op.drop_table("project_script_rows")
