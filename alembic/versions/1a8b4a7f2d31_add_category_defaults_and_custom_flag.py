"""Add category defaults and custom flag

Revision ID: 1a8b4a7f2d31
Revises: 8c7c2d0a5a11
Create Date: 2026-05-27 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1a8b4a7f2d31"
down_revision: Union[str, Sequence[str], None] = "8c7c2d0a5a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_CATEGORIES = [
    ("Groceries", "Supermarkets, food delivery, and daily essentials"),
    ("Dining", "Restaurants, cafes, and takeaway"),
    ("Transport", "Fuel, rides, public transit, and tolls"),
    ("Utilities", "Electricity, water, gas, internet, and mobile"),
    ("Rent", "House rent and lease payments"),
    ("Shopping", "Retail, e-commerce, and personal purchases"),
    ("Entertainment", "Movies, subscriptions, games, and leisure"),
    ("Health", "Doctor visits, pharmacy, and medical expenses"),
    ("Travel", "Flights, hotels, and travel-related spend"),
    ("Education", "Courses, tuition, and learning expenses"),
    ("Salary", "Salary credits and compensation"),
    ("Transfer", "Internal transfers between owned accounts"),
    ("Fees", "Bank fees, charges, and penalties"),
    ("Taxes", "Tax payments and tax-related deductions"),
    ("Investment", "Mutual funds, stocks, SIPs, and brokerage"),
]


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    connection = op.get_bind()
    for name, description in DEFAULT_CATEGORIES:
        connection.execute(
            sa.text(
                """
                INSERT INTO categories (name, description, is_custom)
                VALUES (:name, :description, false)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": name, "description": description},
        )

    op.alter_column("categories", "is_custom", server_default=None)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM categories WHERE name = ANY(:names) AND is_custom = false"
        ),
        {"names": [name for name, _ in DEFAULT_CATEGORIES]},
    )
    op.drop_column("categories", "is_custom")
