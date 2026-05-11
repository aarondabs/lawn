"""fix irrigation_event source check constraint

Revision ID: f3a91b2e8c04
Revises: 7e2f9a1c3d5b
Create Date: 2026-05-07

The original constraint allowed ('rachio','manual','calculated') but these
were placeholder values that never matched the intended source taxonomy.
The correct values come from IRRIGATION_EVENT_SOURCES:
  rachio_scheduled, rachio_manual, rachio_quick_run, manual_logged

Also migrates any existing rows with the old sentinel values:
  'rachio'     -> 'rachio_scheduled'  (most Rachio events are scheduled)
  'manual'     -> 'rachio_manual'
  'calculated' -> 'rachio_scheduled'  (should not exist; map conservatively)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a91b2e8c04"
down_revision: Union[str, None] = "7e2f9a1c3d5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate any existing rows with old values before tightening the constraint
    op.execute(
        "UPDATE irrigation_event SET source = 'rachio_scheduled' WHERE source = 'rachio'"
    )
    op.execute(
        "UPDATE irrigation_event SET source = 'rachio_manual' WHERE source = 'manual'"
    )
    op.execute(
        "UPDATE irrigation_event SET source = 'rachio_scheduled' WHERE source = 'calculated'"
    )

    op.drop_constraint(
        "irrigation_event_source_check",
        "irrigation_event",
        type_="check",
    )
    op.create_check_constraint(
        "irrigation_event_source_check",
        "irrigation_event",
        "source IN ('rachio_scheduled','rachio_manual','rachio_quick_run','manual_logged')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "irrigation_event_source_check",
        "irrigation_event",
        type_="check",
    )
    op.create_check_constraint(
        "irrigation_event_source_check",
        "irrigation_event",
        "source IN ('rachio','manual','calculated')",
    )
