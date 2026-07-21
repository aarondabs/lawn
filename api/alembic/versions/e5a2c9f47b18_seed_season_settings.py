"""phase 2c: seed season-related guardrail settings

Revision ID: e5a2c9f47b18
Revises: d4f1a67c8e23
Create Date: 2026-07-21

Two settings the guardrails need that the first settings migration did not seed:

- nitrogen_lb_per_1000_per_season: the season-to-date N budget. Sourced from the
  CoRoN label's cool-season range (3.75-4.25 lb N/1,000/yr; midpoint 4.0). This
  value was set directly on prod during data entry; seeding it here makes fresh
  installs and the test database consistent with prod.

- season_start_month_day: when the annual-cumulative counters reset. Grub and N
  programs are seasonal, so "once per year" means "once per season" -- an
  application a week earlier than last year's must not count against last
  season's total. Default 03-01 (spring), tunable.

Idempotent: ON CONFLICT DO NOTHING, so it will not clobber an operator-tuned
value already present.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e5a2c9f47b18"
down_revision: Union[str, None] = "d4f1a67c8e23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO app_setting (key, value, description) VALUES
        (
            'nitrogen_lb_per_1000_per_season',
            '4.0'::jsonb,
            'Season-to-date nitrogen ceiling in lb N per 1,000 sq ft, summed across all fertilizers. From the CoRoN cool-season label range 3.75-4.25; midpoint. Advisory.'
        ),
        (
            'season_start_month_day',
            '"03-01"'::jsonb,
            'Month-day the annual cumulative guardrail counters reset (season start). Keeps "once per season" from tripping on an application slightly earlier than last year.'
        )
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM app_setting WHERE key IN "
        "('nitrogen_lb_per_1000_per_season', 'season_start_month_day')"
    )
