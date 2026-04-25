"""app settings and provider credentials

Revision ID: 20260424_0003
Revises: 20260424_0002
Create Date: 2026-04-24 01:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260424_0003"
down_revision = "20260424_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("namespace", "key", name="uq_app_settings_namespace_key"),
    )
    op.create_index("ix_app_settings_namespace", "app_settings", ["namespace"])
    op.create_index("ix_app_settings_key", "app_settings", ["key"])


def downgrade() -> None:
    op.drop_index("ix_app_settings_key", table_name="app_settings")
    op.drop_index("ix_app_settings_namespace", table_name="app_settings")
    op.drop_table("app_settings")
