"""phase 2c: app_setting table and guardrail product fields

Revision ID: d4f1a67c8e23
Revises: c3e8b41d92f6
Create Date: 2026-07-20

Three additions the Phase 2c guardrail and reminder work needs, none of which
existed:

1. `app_setting` -- a typed key/value store for operator-tunable thresholds.
   Task 1.1 requires the nitrogen limit be "a setting, not a magic number", and
   Task 4.1 wants reminder rules to be data-driven config rather than hardcoded
   conditionals. Neither had anywhere to live.

2. `product.reorder_threshold` -- Task 4.2's low-stock trigger. Deliberately
   carries no unit of its own: it is compared against `current_inventory` and
   must therefore share `current_inventory_unit`. A second unit column would
   only create a way for the two to disagree.

3. `product.preemergent_blocking_days` -- Task 1.4's germination-blocking window
   after a pre-emergent application. Product-specific, and only meaningful for
   `herbicide_pre`, so it is nullable; the guardrail falls back to a conservative
   default and says so when it is unset.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4f1a67c8e23"
down_revision: Union[str, None] = "c3e8b41d92f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_setting",
        sa.Column("key", sa.Text(), nullable=False),
        # JSONB rather than text so a setting can be a number, string, boolean or
        # small object without every reader having to parse and coerce.
        sa.Column("value", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.add_column("product", sa.Column("reorder_threshold", sa.Numeric(), nullable=True))
    op.create_check_constraint(
        "product_reorder_threshold_non_negative",
        "product",
        "reorder_threshold IS NULL OR reorder_threshold >= 0",
    )

    op.add_column("product", sa.Column("preemergent_blocking_days", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "product_preemergent_blocking_days_positive",
        "product",
        "preemergent_blocking_days IS NULL OR preemergent_blocking_days > 0",
    )

    # Seed the thresholds Phase 2c refers to by name, so the guardrails have
    # defaults on first run rather than failing to evaluate.
    op.execute(
        """
        INSERT INTO app_setting (key, value, description) VALUES
        (
            'nitrogen_lb_per_1000_per_30d',
            '1.0'::jsonb,
            'Trailing 30-day nitrogen ceiling in lb N per 1,000 sq ft. Advisory only -- exceeding it warns, never blocks.'
        ),
        (
            'preemergent_blocking_days_default',
            '90'::jsonb,
            'Conservative fallback for how long a pre-emergent blocks seed germination when the product record does not say.'
        ),
        (
            'days_since_mow_threshold',
            '10'::jsonb,
            'Days without a mow during the growing season before a reminder fires.'
        ),
        (
            'soil_temp_preemergent_f',
            '55'::jsonb,
            'Sustained soil temperature (F) that opens the spring pre-emergent window.'
        )
        """
    )


def downgrade() -> None:
    op.drop_constraint("product_preemergent_blocking_days_positive", "product", type_="check")
    op.drop_column("product", "preemergent_blocking_days")
    op.drop_constraint("product_reorder_threshold_non_negative", "product", type_="check")
    op.drop_column("product", "reorder_threshold")
    op.drop_table("app_setting")
