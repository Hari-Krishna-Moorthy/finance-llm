"""Add dashboard state table

Revision ID: 5b8f9c1d7a20
Revises: 3e4f1d2c9b55
Create Date: 2026-05-27 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5b8f9c1d7a20"
down_revision: Union[str, Sequence[str], None] = "3e4f1d2c9b55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboard_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_dashboard_state_id"), "dashboard_state", ["id"], unique=False)
    op.create_index(op.f("ix_dashboard_state_key"), "dashboard_state", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_dashboard_state_key"), table_name="dashboard_state")
    op.drop_index(op.f("ix_dashboard_state_id"), table_name="dashboard_state")
    op.drop_table("dashboard_state")
