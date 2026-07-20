"""phase 2a: application_method NOT NULL

Revision ID: b2d5f8a13c47
Revises: a1c4e7b92f03
Create Date: 2026-07-20

Migration B of two. Migration A added treatment.application_method as nullable
so existing rows could be labelled; this locks it down now that they have been.

The four pre-refactor treatments were labelled from the equipment already linked
to them -- the two Fimco sprayer jobs are liquid, the two Echo spreader jobs are
granular. The liquid pair keep their flat treatment_product rows rather than
having tank fills reconstructed: the fill detail was never recorded, and
inventing it would be fabrication, not migration.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2d5f8a13c47"
down_revision: Union[str, None] = "a1c4e7b92f03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPLICATION_METHODS = ("granular", "liquid", "other")


def _in_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # Fail loudly rather than silently defaulting: an unlabelled row here means
    # the interactive backfill was skipped, and guessing a method would be wrong.
    connection = op.get_bind()
    unlabelled = connection.execute(
        sa.text("SELECT count(*) FROM treatment WHERE application_method IS NULL")
    ).scalar()
    if unlabelled:
        raise RuntimeError(
            f"{unlabelled} treatment row(s) still have a NULL application_method. "
            "Label them before running this migration."
        )

    op.alter_column("treatment", "application_method", nullable=False)
    # Tighten the CHECK now that NULL is no longer permitted.
    op.drop_constraint("treatment_application_method_check", "treatment", type_="check")
    op.create_check_constraint(
        "treatment_application_method_check",
        "treatment",
        f"application_method IN ({_in_list(APPLICATION_METHODS)})",
    )


def downgrade() -> None:
    op.drop_constraint("treatment_application_method_check", "treatment", type_="check")
    op.create_check_constraint(
        "treatment_application_method_check",
        "treatment",
        f"application_method IS NULL OR application_method IN ({_in_list(APPLICATION_METHODS)})",
    )
    op.alter_column("treatment", "application_method", nullable=True)
