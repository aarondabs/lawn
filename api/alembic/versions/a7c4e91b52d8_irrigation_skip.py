"""phase 2c: irrigation_skip table for Rachio schedule skips

Revision ID: a7c4e91b52d8
Revises: f6b3d18a2c94
Create Date: 2026-07-21

Rachio emits schedule-level skip events (rain, seasonal shift) that the poller
previously dropped -- they have no zone or duration, so they never fit
irrigation_event. This table captures them for the "Rachio skipped watering N
times this week" signal. Idempotent by rachio_event_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c4e91b52d8"
down_revision: Union[str, None] = "f6b3d18a2c94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "irrigation_skip",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("rachio_event_id", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("subtype", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), server_default=sa.text("'rachio'"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rachio_event_id", name="irrigation_skip_rachio_event_id_uniq"),
    )
    op.create_index("ix_irrigation_skip_occurred_at", "irrigation_skip", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_irrigation_skip_occurred_at", table_name="irrigation_skip")
    op.drop_table("irrigation_skip")
