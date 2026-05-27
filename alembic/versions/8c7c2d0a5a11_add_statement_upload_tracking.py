"""Add statement upload tracking

Revision ID: 8c7c2d0a5a11
Revises: c2285fd064e6
Create Date: 2026-05-27 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c7c2d0a5a11"
down_revision: Union[str, Sequence[str], None] = "c2285fd064e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "statement_uploads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("has_password", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.String(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_statement_uploads_id"), "statement_uploads", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_statement_uploads_id"), table_name="statement_uploads")
    op.drop_table("statement_uploads")
