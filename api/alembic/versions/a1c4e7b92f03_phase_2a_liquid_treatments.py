"""phase 2a: liquid/granular treatment split

Revision ID: a1c4e7b92f03
Revises: f3a91b2e8c04
Create Date: 2026-07-20

Migration A of two. Additive only -- treatment_product is untouched and remains
the granular path.

1. Add treatment.application_method, NULLABLE for now. Migration B sets it NOT
   NULL once existing rows are labelled.
2. Create tank_fill (one sprayer tank) and fill_product (what went into it).
3. Repoint product.current_inventory_unit at amount units. It previously checked
   against RATE_UNITS, so the only expressible stock level was something like
   "0 lb_per_1000" -- a rate, not a quantity, and unusable for decrement.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c4e7b92f03"
down_revision: Union[str, None] = "f3a91b2e8c04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AMOUNT_UNITS = ("fl_oz", "pt", "qt", "gal", "oz", "lb")
APPLICATION_METHODS = ("granular", "liquid", "other")
MIX_VOLUME_UNITS = ("gal", "l")
CALIBRATED_RATE_UNITS = ("gal_per_1000", "fl_oz_per_1000")
RATE_UNITS = (
    "lb_per_1000",
    "oz_per_1000",
    "fl_oz_per_1000",
    "gal_per_1000",
    "fl_oz_per_gal",
    "pct_vv",
    "lb_per_acre",
)


def _in_list(values: Sequence[str]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # --- 1. treatment.application_method (nullable until Migration B) --------
    op.add_column("treatment", sa.Column("application_method", sa.Text(), nullable=True))
    op.create_check_constraint(
        "treatment_application_method_check",
        "treatment",
        f"application_method IS NULL OR application_method IN ({_in_list(APPLICATION_METHODS)})",
    )

    # --- 2. tank_fill --------------------------------------------------------
    op.create_table(
        "tank_fill",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("treatment_id", sa.UUID(), nullable=False),
        sa.Column("fill_number", sa.Integer(), nullable=False),
        sa.Column("total_mix_volume", sa.Numeric(), nullable=False),
        sa.Column(
            "total_mix_volume_unit", sa.Text(), server_default=sa.text("'gal'"), nullable=False
        ),
        sa.Column("calibrated_rate_snapshot", sa.Numeric(), nullable=False),
        sa.Column(
            "calibrated_rate_unit_snapshot",
            sa.Text(),
            server_default=sa.text("'gal_per_1000'"),
            nullable=False,
        ),
        sa.Column("area_covered_sqft", sa.Numeric(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["treatment_id"], ["treatment.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("treatment_id", "fill_number", name="tank_fill_treatment_fill_number_uniq"),
        sa.CheckConstraint(
            f"total_mix_volume_unit IN ({_in_list(MIX_VOLUME_UNITS)})",
            name="tank_fill_total_mix_volume_unit_check",
        ),
        sa.CheckConstraint(
            f"calibrated_rate_unit_snapshot IN ({_in_list(CALIBRATED_RATE_UNITS)})",
            name="tank_fill_calibrated_rate_unit_snapshot_check",
        ),
        sa.CheckConstraint("total_mix_volume > 0", name="tank_fill_total_mix_volume_positive"),
        sa.CheckConstraint("calibrated_rate_snapshot > 0", name="tank_fill_calibrated_rate_positive"),
        sa.CheckConstraint("fill_number > 0", name="tank_fill_fill_number_positive"),
    )
    op.create_index("ix_tank_fill_treatment_id", "tank_fill", ["treatment_id"])

    # --- 3. fill_product -----------------------------------------------------
    op.create_table(
        "fill_product",
        sa.Column("tank_fill_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("amount_used", sa.Numeric(), nullable=False),
        sa.Column("amount_used_unit", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["tank_fill_id"], ["tank_fill.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("tank_fill_id", "product_id"),
        sa.CheckConstraint(
            f"amount_used_unit IN ({_in_list(AMOUNT_UNITS)})",
            name="fill_product_amount_used_unit_check",
        ),
        sa.CheckConstraint("amount_used > 0", name="fill_product_amount_used_positive"),
    )
    op.create_index("ix_fill_product_product_id", "fill_product", ["product_id"])

    # --- 4. product.current_inventory_unit -> amount units -------------------
    # The single existing value is '0 lb_per_1000', which is not a real stock
    # level. Null it out rather than pretend it maps onto a quantity unit.
    op.execute(
        "UPDATE product SET current_inventory = NULL, current_inventory_unit = NULL "
        "WHERE current_inventory_unit IS NOT NULL"
    )
    op.drop_constraint("product_current_inventory_unit_check", "product", type_="check")
    op.create_check_constraint(
        "product_current_inventory_unit_check",
        "product",
        f"current_inventory_unit IS NULL OR current_inventory_unit IN ({_in_list(AMOUNT_UNITS)})",
    )


def downgrade() -> None:
    op.drop_constraint("product_current_inventory_unit_check", "product", type_="check")
    op.create_check_constraint(
        "product_current_inventory_unit_check",
        "product",
        f"current_inventory_unit IS NULL OR current_inventory_unit IN ({_in_list(RATE_UNITS)})",
    )

    op.drop_index("ix_fill_product_product_id", table_name="fill_product")
    op.drop_table("fill_product")
    op.drop_index("ix_tank_fill_treatment_id", table_name="tank_fill")
    op.drop_table("tank_fill")

    op.drop_constraint("treatment_application_method_check", "treatment", type_="check")
    op.drop_column("treatment", "application_method")
