"""Add transaction extra details json

Revision ID: 3e4f1d2c9b55
Revises: 1a8b4a7f2d31
Create Date: 2026-05-27 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3e4f1d2c9b55"
down_revision: Union[str, Sequence[str], None] = "1a8b4a7f2d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("extra_details", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "extra_details")
