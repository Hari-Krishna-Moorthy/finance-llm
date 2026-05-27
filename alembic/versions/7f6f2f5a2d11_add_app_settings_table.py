"""Add app settings table

Revision ID: 7f6f2f5a2d11
Revises: 5b8f9c1d7a20
Create Date: 2026-05-27 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f6f2f5a2d11"
down_revision: Union[str, Sequence[str], None] = "5b8f9c1d7a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_app_settings_id"), "app_settings", ["id"], unique=False)
    op.create_index(op.f("ix_app_settings_key"), "app_settings", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_app_settings_key"), table_name="app_settings")
    op.drop_index(op.f("ix_app_settings_id"), table_name="app_settings")
    op.drop_table("app_settings")
