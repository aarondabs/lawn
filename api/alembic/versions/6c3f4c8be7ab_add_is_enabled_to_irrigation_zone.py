"""add is_enabled to irrigation_zone

Revision ID: 6c3f4c8be7ab
Revises: 2a08c9d24ed9
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6c3f4c8be7ab"
down_revision: Union[str, None] = "2a08c9d24ed9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE irrigation_zone ADD COLUMN IF NOT EXISTS is_enabled boolean NOT NULL DEFAULT true"
    )


def downgrade() -> None:
    op.drop_column("irrigation_zone", "is_enabled")
