"""phase 1.5: tank mix schema refactor

Revision ID: 7e2f9a1c3d5b
Revises: 5a1f83f2d8b4
Create Date: 2026-05-11

Schema changes for tank mix support:
1. Create treatment_product join table with composite PK (treatment_id, product_id)
2. Drop product_id, rate_applied, rate_unit from treatment (table is empty)
3. Expand product_type CHECK constraint
4. Expand rate_unit CHECK constraint on both product and new treatment_product
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7e2f9a1c3d5b"
down_revision: Union[str, None] = "5a1f83f2d8b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create treatment_product table
    op.create_table(
        "treatment_product",
        sa.Column("treatment_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("rate_applied", sa.Numeric(), nullable=False),
        sa.Column(
            "rate_unit",
            sa.Text(),
            nullable=False,
            server_default="fl_oz_per_1000",
        ),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["treatment_id"], ["treatment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("treatment_id", "product_id"),
        sa.CheckConstraint(
            "rate_unit IN ('lb_per_1000','oz_per_1000','fl_oz_per_1000','gal_per_1000',"
            "'fl_oz_per_gal','pct_vv','lb_per_acre')",
            name="treatment_product_rate_unit_check",
        ),
    )

    # Create index on product_id for efficient lookups
    op.create_index(
        "ix_treatment_product_product_id",
        "treatment_product",
        ["product_id"],
        unique=False,
    )

    # Drop legacy constraints defensively; prior schemas may use different names.
    op.execute("ALTER TABLE treatment DROP CONSTRAINT IF EXISTS treatment_product_id_fkey")
    op.execute("ALTER TABLE treatment DROP CONSTRAINT IF EXISTS treatment_rate_unit_check")

    # Drop columns from treatment (safe - table is empty)
    op.drop_column("treatment", "rate_unit")
    op.drop_column("treatment", "rate_applied")
    op.drop_column("treatment", "product_id")

    # Drop legacy product constraints before remapping legacy values.
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_product_type_check")
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_label_rate_unit_check")
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_current_inventory_unit_check")
    op.execute("ALTER TABLE product DROP CONSTRAINT IF EXISTS product_max_annual_rate_unit_check")

    # Normalize legacy product values so new CHECK constraints can be applied.
    op.execute(
        """
        UPDATE product
        SET product_type = CASE product_type
            WHEN 'fertilizer' THEN 'fertilizer_synthetic'
            WHEN 'herbicide_post' THEN 'herbicide_post_broadleaf'
            ELSE product_type
        END
        """
    )

    op.execute(
        """
        UPDATE product
        SET label_rate_unit = CASE label_rate_unit
            WHEN 'lb' THEN 'lb_per_1000'
            WHEN 'oz' THEN 'oz_per_1000'
            WHEN 'fl_oz' THEN 'fl_oz_per_1000'
            WHEN 'gal' THEN 'gal_per_1000'
            ELSE label_rate_unit
        END
        """
    )

    op.execute(
        """
        UPDATE product
        SET current_inventory_unit = CASE current_inventory_unit
            WHEN 'lb' THEN 'lb_per_1000'
            WHEN 'oz' THEN 'oz_per_1000'
            WHEN 'fl_oz' THEN 'fl_oz_per_1000'
            WHEN 'gal' THEN 'gal_per_1000'
            ELSE current_inventory_unit
        END
        WHERE current_inventory_unit IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE product
        SET max_annual_rate_unit = CASE max_annual_rate_unit
            WHEN 'lb' THEN 'lb_per_1000'
            WHEN 'oz' THEN 'oz_per_1000'
            WHEN 'fl_oz' THEN 'fl_oz_per_1000'
            WHEN 'gal' THEN 'gal_per_1000'
            ELSE max_annual_rate_unit
        END
        WHERE max_annual_rate_unit IS NOT NULL
        """
    )

    # Product-specific remaps from Phase 1.5 migration plan.
    op.execute(
        """
        UPDATE product
        SET product_type = 'herbicide_post_broadleaf',
            label_rate_unit = 'fl_oz_per_1000'
        WHERE name = '3-Way Max Turf & Ornamental'
        """
    )
    op.execute(
        """
        UPDATE product
        SET product_type = 'fertilizer_synthetic',
            label_rate_unit = 'fl_oz_per_1000'
        WHERE name = 'CoRoN 28-0-0'
        """
    )
    op.execute(
        """
        UPDATE product
        SET name = 'Southern Ag Surfactant L.A.',
            product_type = 'surfactant',
            label_rate = 1.5,
            label_rate_unit = 'fl_oz_per_gal'
        WHERE name = 'Surfactant for Herbicides'
        """
    )

    # Update product.product_type CHECK constraint
    op.create_check_constraint(
        "product_product_type_check",
        "product",
        "product_type IN ('fertilizer_synthetic','fertilizer_organic','herbicide_pre',"
        "'herbicide_post_broadleaf','herbicide_post_grassy','herbicide_non_selective',"
        "'fungicide','insecticide','biostimulant','soil_amendment','surfactant',"
        "'wetting_agent','dye_marker','seed','other')",
    )

    # Update product.label_rate_unit CHECK constraint
    op.create_check_constraint(
        "product_label_rate_unit_check",
        "product",
        "label_rate_unit IN ('lb_per_1000','oz_per_1000','fl_oz_per_1000','gal_per_1000',"
        "'fl_oz_per_gal','pct_vv','lb_per_acre')",
    )

    # Update product.current_inventory_unit and max_annual_rate_unit CHECK constraints
    op.create_check_constraint(
        "product_current_inventory_unit_check",
        "product",
        "current_inventory_unit IS NULL OR current_inventory_unit IN ('lb_per_1000',"
        "'oz_per_1000','fl_oz_per_1000','gal_per_1000','fl_oz_per_gal','pct_vv','lb_per_acre')",
    )
    op.create_check_constraint(
        "product_max_annual_rate_unit_check",
        "product",
        "max_annual_rate_unit IS NULL OR max_annual_rate_unit IN ('lb_per_1000',"
        "'oz_per_1000','fl_oz_per_1000','gal_per_1000','fl_oz_per_gal','pct_vv','lb_per_acre')",
    )


def downgrade() -> None:
    # Reverse product constraints
    op.drop_constraint("product_max_annual_rate_unit_check", "product", type_="check")
    op.drop_constraint("product_current_inventory_unit_check", "product", type_="check")
    op.drop_constraint("product_label_rate_unit_check", "product", type_="check")
    op.drop_constraint("product_product_type_check", "product", type_="check")

    # Recreate old product constraints
    op.create_check_constraint(
        "product_product_type_check",
        "product",
        "product_type IN ('fertilizer','herbicide_pre','herbicide_post','fungicide',"
        "'insecticide','biostimulant','soil_amendment','seed','other')",
    )
    op.create_check_constraint(
        "product_label_rate_unit_check",
        "product",
        "label_rate_unit IN ('lb','oz','fl_oz','gal')",
    )
    op.create_check_constraint(
        "product_current_inventory_unit_check",
        "product",
        "current_inventory_unit IS NULL OR current_inventory_unit IN ('lb','oz','fl_oz','gal')",
    )
    op.create_check_constraint(
        "product_max_annual_rate_unit_check",
        "product",
        "max_annual_rate_unit IS NULL OR max_annual_rate_unit IN ('lb','oz','fl_oz','gal')",
    )

    # Restore treatment columns
    op.add_column(
        "treatment",
        sa.Column("product_id", sa.UUID(), nullable=False, server_default="gen_random_uuid()"),
    )
    op.add_column(
        "treatment",
        sa.Column("rate_applied", sa.Numeric(), nullable=False, server_default="0"),
    )
    op.add_column(
        "treatment",
        sa.Column("rate_unit", sa.Text(), nullable=False, server_default="fl_oz"),
    )

    # Restore foreign key
    op.create_foreign_key(
        "treatment_product_id_fkey",
        "treatment",
        "product",
        ["product_id"],
        ["id"],
    )

    # Restore treatment CHECK constraint
    op.create_check_constraint(
        "treatment_rate_unit_check",
        "treatment",
        "rate_unit IN ('lb','oz','fl_oz','gal')",
    )

    # Drop treatment_product table and index
    op.drop_index("ix_treatment_product_product_id", table_name="treatment_product")
    op.drop_table("treatment_product")
