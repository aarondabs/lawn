"""create timeseries tables

Revision ID: c7dab2e13bd7
Revises: da5a66c32ed2
Create Date: 2026-05-05

Creates the two tables that will become TimescaleDB hypertables in the next
revision.  They are created as regular Postgres tables here so that this
revision is cleanly reversible without needing TimescaleDB.

Hypertable design notes:
- weather_observation: PK (observed_at, source); partitioned on observed_at
- irrigation_event: PK (started_at, zone_id); partitioned on started_at

Both tables skip UUID primary keys by design — see DATA_MODEL.md.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7dab2e13bd7"
down_revision: Union[str, None] = "da5a66c32ed2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # weather_observation                                                #
    # Will be converted to a hypertable in the next revision.            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "weather_observation",
        sa.Column("observed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("temp_f", sa.Numeric(), nullable=True),
        sa.Column("humidity_pct", sa.Numeric(), nullable=True),
        sa.Column("dew_point_f", sa.Numeric(), nullable=True),
        sa.Column("wind_mph", sa.Numeric(), nullable=True),
        sa.Column("wind_gust_mph", sa.Numeric(), nullable=True),
        sa.Column("precip_in", sa.Numeric(), nullable=True),
        sa.Column("soil_temp_f", sa.Numeric(), nullable=True),
        sa.Column("et0_in", sa.Numeric(), nullable=True),
        sa.Column("gdd_base50", sa.Numeric(), nullable=True),
        sa.PrimaryKeyConstraint("observed_at", "source"),
    )

    # ------------------------------------------------------------------ #
    # irrigation_event                                                   #
    # Will be converted to a hypertable in the next revision.            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "irrigation_event",
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("zone_id", sa.UUID(), nullable=False),
        sa.Column("rachio_event_id", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("precip_rate_in_per_hr_snapshot", sa.Numeric(4, 2), nullable=False),
        sa.Column(
            "inches_applied",
            sa.Numeric(6, 3),
            sa.Computed(
                "duration_seconds / 3600.0 * precip_rate_in_per_hr_snapshot",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("skipped", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "source IN ('rachio','manual','calculated')",
            name="irrigation_event_source_check",
        ),
        sa.ForeignKeyConstraint(["zone_id"], ["irrigation_zone.id"]),
        sa.PrimaryKeyConstraint("started_at", "zone_id"),
    )
    # TimescaleDB requires all unique indexes to include the partitioning column.
    # (rachio_event_id, started_at) is still an effective deduplication key because
    # a given Rachio event always has the same start time.
    op.create_index(
        "irrigation_event_rachio_event_id_uniq",
        "irrigation_event",
        ["rachio_event_id", "started_at"],
        unique=True,
        postgresql_where=sa.text("rachio_event_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("irrigation_event_rachio_event_id_uniq", table_name="irrigation_event", if_exists=True)
    op.drop_table("irrigation_event")
    op.drop_table("weather_observation")
