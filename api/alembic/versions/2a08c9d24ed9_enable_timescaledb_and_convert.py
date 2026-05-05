"""enable timescaledb and convert hypertables

Revision ID: 2a08c9d24ed9
Revises: c7dab2e13bd7
Create Date: 2026-05-05

Enables the TimescaleDB extension and converts weather_observation and
irrigation_event to hypertables.

IMPORTANT — downgrade behavior:
TimescaleDB does NOT support converting a hypertable back to a regular
table in-place.  The downgrade here drops and recreates the tables as
plain Postgres tables (losing data).  This is acceptable for the lawn
app (single-user, dev environment).  Do NOT run downgrade on a table with
data you want to keep.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2a08c9d24ed9"
down_revision: Union[str, None] = "c7dab2e13bd7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    # Partition interval: 1 month for hourly weather observations.
    op.execute(
        """
        SELECT create_hypertable(
            'weather_observation',
            'observed_at',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        )
        """
    )

    # Partition interval: 3 months for irrigation events (lower write volume).
    op.execute(
        """
        SELECT create_hypertable(
            'irrigation_event',
            'started_at',
            chunk_time_interval => INTERVAL '3 months',
            if_not_exists => TRUE
        )
        """
    )


def downgrade() -> None:
    # See module docstring — data loss is expected.
    op.execute("DROP INDEX IF EXISTS irrigation_event_rachio_event_id_uniq")
    op.drop_table("irrigation_event")
    op.drop_table("weather_observation")

    # Recreate as plain tables (mirrors revision c7dab2e13bd7 upgrade)
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
    op.create_index(
        "irrigation_event_rachio_event_id_uniq",
        "irrigation_event",
        ["rachio_event_id"],
        unique=True,
        postgresql_where=sa.text("rachio_event_id IS NOT NULL"),
    )
    op.execute("DROP EXTENSION IF EXISTS timescaledb")
