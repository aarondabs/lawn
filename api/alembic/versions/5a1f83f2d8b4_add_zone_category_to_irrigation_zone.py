"""add zone_category to irrigation_zone

Revision ID: 5a1f83f2d8b4
Revises: 6c3f4c8be7ab
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5a1f83f2d8b4"
down_revision: Union[str, None] = "6c3f4c8be7ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "irrigation_zone",
        sa.Column("zone_category", sa.Text(), nullable=False, server_default=sa.text("'turf'")),
    )
    op.create_check_constraint(
        "irrigation_zone_zone_category_check",
        "irrigation_zone",
        "zone_category IN ('turf','trees_shrubs','ornamental','inactive')",
    )


def downgrade() -> None:
    op.drop_constraint("irrigation_zone_zone_category_check", "irrigation_zone", type_="check")
    op.drop_column("irrigation_zone", "zone_category")
