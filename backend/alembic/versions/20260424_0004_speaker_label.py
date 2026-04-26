"""project_script_rows.speaker_label for dialogue mode

Revision ID: 20260424_0004
Revises: 20260424_0003
Create Date: 2026-04-25 18:30:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260424_0004"
down_revision = "20260424_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_script_rows",
        sa.Column("speaker_label", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_script_rows", "speaker_label")
