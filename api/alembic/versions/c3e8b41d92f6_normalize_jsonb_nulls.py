"""phase 2c: normalize JSONB 'null' to SQL NULL

Revision ID: c3e8b41d92f6
Revises: b2d5f8a13c47
Create Date: 2026-07-20

SQLAlchemy's JSONB type renders Python None as the JSON scalar 'null' unless the
column sets none_as_null=True. Every nullable JSONB column in this schema was
built without it, so "no value" was stored two different ways depending on the
path -- and `WHERE col IS NULL` matched only one of them, silently.

This bit the Phase 2a mow backfill, which reported `UPDATE 0` against 13 rows
that all looked null. It was caught there only because the row count was
obviously wrong. A guardrail asking "which fertilizers are missing a guaranteed
analysis?" would instead return an empty list and read as all-clear.

The models now set none_as_null=True; this migration brings existing rows into
line so the two agree. equipment.calibration currently holds one of each, which
is the inconsistency made concrete.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c3e8b41d92f6"
down_revision: Union[str, None] = "b2d5f8a13c47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column) for every nullable JSONB column in the schema.
JSONB_COLUMNS: tuple[tuple[str, str], ...] = (
    ("cultural_practice", "details"),
    ("equipment", "calibration"),
    ("product", "active_ingredients"),
    ("product", "guaranteed_analysis"),
    ("soil_test", "base_saturation"),
)


def upgrade() -> None:
    for table, column in JSONB_COLUMNS:
        op.execute(
            f"UPDATE {table} SET {column} = NULL WHERE jsonb_typeof({column}) = 'null'"  # noqa: S608
        )


def downgrade() -> None:
    # Deliberately not reversed. Rewriting SQL NULL back to JSON 'null' would
    # reintroduce the defect, and it cannot distinguish rows that were already
    # SQL NULL before this ran from those this migration converted.
    pass
