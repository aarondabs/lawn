"""phase 2c: weather_daily table for GDD accumulation

Revision ID: f6b3d18a2c94
Revises: e5a2c9f47b18
Create Date: 2026-07-21

Growing-degree-days need a persistent per-day record. weather_forecast holds
daily highs and lows but is wiped and rewritten every refresh (a rolling 17-day
window), so it cannot accumulate a season. weather_daily is upserted and never
purged.

Also drops weather_observation.gdd_base50. What it stored was not GDD at all --
`instantaneous air temp - 50` at poll time, one snapshot per poll, un-summable.
Nothing reads it (verified), so it goes rather than lingering as a misleading
dead column. Real daily GDD lives on weather_daily, computed in the service
layer as max(0, (high+low)/2 - 50) and left NULL when a day lacks a temperature.

Seeds gdd_green_up_month_day: the season-start date GDD accumulates from.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6b3d18a2c94"
down_revision: Union[str, None] = "e5a2c9f47b18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weather_daily",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("temp_high_f", sa.Numeric(), nullable=True),
        sa.Column("temp_low_f", sa.Numeric(), nullable=True),
        sa.Column("gdd_base50", sa.Numeric(), nullable=True),
        sa.Column("precip_sum_in", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("observation_date", "source", name="weather_daily_date_source_uniq"),
    )
    op.create_index("ix_weather_daily_date", "weather_daily", ["observation_date"])

    op.drop_column("weather_observation", "gdd_base50")

    op.execute(
        """
        INSERT INTO app_setting (key, value, description) VALUES
        (
            'gdd_green_up_month_day',
            '"03-15"'::jsonb,
            'Month-day GDD accumulation starts from each year (spring green-up). Base 50F, for cool-season TTTF.'
        )
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM app_setting WHERE key = 'gdd_green_up_month_day'")
    op.add_column("weather_observation", sa.Column("gdd_base50", sa.Numeric(), nullable=True))
    op.drop_index("ix_weather_daily_date", table_name="weather_daily")
    op.drop_table("weather_daily")
