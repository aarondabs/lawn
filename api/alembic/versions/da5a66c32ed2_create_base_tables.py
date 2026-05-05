"""create base tables

Revision ID: da5a66c32ed2
Revises: bb1c6cb831ed
Create Date: 2026-05-05

Creates all non-hypertable Phase 1 tables:
  lawn_profile, irrigation_zone, equipment, product, treatment,
  cultural_practice, soil_test, weather_forecast, reminder

Includes:
- CHECK constraints on all closed-set text enums
- lawn_profile singleton guard unique constraint
- weather_forecast generated day column (America/Chicago) with unique constraint
- irrigation_zone zone_number unique constraint
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "da5a66c32ed2"
down_revision: Union[str, None] = "bb1c6cb831ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # lawn_profile                                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "lawn_profile",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("singleton_guard", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("total_sqft", sa.Integer(), nullable=False),
        sa.Column("grass_type", sa.Text(), server_default="TTTF", nullable=False),
        sa.Column("establishment_date", sa.Date(), nullable=True),
        sa.Column("target_mow_height_inches", sa.Numeric(3, 1), nullable=False),
        sa.Column("latitude", sa.Numeric(8, 5), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 5), nullable=False),
        sa.Column("usda_zone", sa.Text(), server_default="6a", nullable=False),
        sa.Column("climate_notes", sa.Text(), nullable=True),
        sa.Column("soil_type", sa.Text(), nullable=False),
        sa.Column("water_source", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "soil_type IN ('sand','sandy_loam','loam','silty_loam','silty_clay_loam','clay_loam','clay')",
            name="lawn_profile_soil_type_check",
        ),
        sa.CheckConstraint(
            "water_source IN ('city','well','mixed')",
            name="lawn_profile_water_source_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_guard", name="lawn_profile_singleton"),
    )

    # ------------------------------------------------------------------ #
    # irrigation_zone                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "irrigation_zone",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("rachio_zone_id", sa.Text(), nullable=True),
        sa.Column("zone_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("head_type", sa.Text(), nullable=False),
        sa.Column("nozzle_gpm", sa.Numeric(5, 2), nullable=True),
        sa.Column("precipitation_rate_in_per_hr", sa.Numeric(4, 2), nullable=True),
        sa.Column("sun_exposure", sa.Text(), nullable=False),
        sa.Column("slope", sa.Text(), nullable=False),
        sa.Column("soil_type_override", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "head_type IN ('rotor','spray','mp_rotator','drip','hybrid')",
            name="irrigation_zone_head_type_check",
        ),
        sa.CheckConstraint(
            "sun_exposure IN ('full_sun','partial_sun','partial_shade','full_shade')",
            name="irrigation_zone_sun_exposure_check",
        ),
        sa.CheckConstraint(
            "slope IN ('flat','mild','moderate','steep')",
            name="irrigation_zone_slope_check",
        ),
        sa.CheckConstraint(
            "soil_type_override IS NULL OR soil_type_override IN ('sand','sandy_loam','loam','silty_loam','silty_clay_loam','clay_loam','clay')",
            name="irrigation_zone_soil_type_override_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rachio_zone_id", name="irrigation_zone_rachio_id_uniq"),
        sa.UniqueConstraint("zone_number", name="irrigation_zone_zone_number_uniq"),
    )

    # ------------------------------------------------------------------ #
    # equipment                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "equipment",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("make", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("calibration", JSONB(), nullable=True),
        sa.Column("last_calibration_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('sprayer','spreader','aerator','dethatcher','mower','edger','other')",
            name="equipment_type_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # product                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "product",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("manufacturer", sa.Text(), nullable=False),
        sa.Column("product_type", sa.Text(), nullable=False),
        sa.Column("active_ingredients", JSONB(), nullable=True),
        sa.Column("guaranteed_analysis", JSONB(), nullable=True),
        sa.Column("label_rate", sa.Numeric(), nullable=False),
        sa.Column("label_rate_unit", sa.Text(), nullable=False),
        sa.Column("reentry_interval_hours", sa.Integer(), nullable=True),
        sa.Column("min_reapplication_days", sa.Integer(), nullable=True),
        sa.Column("max_annual_rate", sa.Numeric(), nullable=True),
        sa.Column("max_annual_rate_unit", sa.Text(), nullable=True),
        sa.Column("current_inventory", sa.Numeric(), nullable=True),
        sa.Column("current_inventory_unit", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "product_type IN ('fertilizer','herbicide_pre','herbicide_post','fungicide','insecticide','biostimulant','soil_amendment','seed','other')",
            name="product_product_type_check",
        ),
        sa.CheckConstraint(
            "label_rate_unit IN ('lb','oz','fl_oz','gal')",
            name="product_label_rate_unit_check",
        ),
        sa.CheckConstraint(
            "current_inventory_unit IS NULL OR current_inventory_unit IN ('lb','oz','fl_oz','gal')",
            name="product_current_inventory_unit_check",
        ),
        sa.CheckConstraint(
            "max_annual_rate_unit IS NULL OR max_annual_rate_unit IN ('lb','oz','fl_oz','gal')",
            name="product_max_annual_rate_unit_check",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # treatment                                                            #
    # ------------------------------------------------------------------ #
    # Note: total_amount and total_amount_unit are intentionally omitted.
    # They are computed at API serialization time:
    #   total_amount = rate_applied × area_treated_sqft / 1000
    #   total_amount_unit = rate_unit
    op.create_table(
        "treatment",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("applied_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("rate_applied", sa.Numeric(), nullable=False),
        sa.Column("rate_unit", sa.Text(), nullable=False),
        sa.Column("area_treated_sqft", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=True),
        sa.Column("applicator", sa.Text(), nullable=False),
        sa.Column("weather_temp_f", sa.Numeric(), nullable=True),
        sa.Column("weather_wind_mph", sa.Numeric(), nullable=True),
        sa.Column("weather_conditions", sa.Text(), nullable=True),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rate_unit IN ('lb','oz','fl_oz','gal')",
            name="treatment_rate_unit_check",
        ),
        sa.CheckConstraint(
            "applicator IN ('self','spouse','lawn_service','other')",
            name="treatment_applicator_check",
        ),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # cultural_practice                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "cultural_practice",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("performed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("practice_type", sa.Text(), nullable=False),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("equipment_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "practice_type IN ('mow','aerate','dethatch','overseed','scalp','leveling','edge','other')",
            name="cultural_practice_practice_type_check",
        ),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # soil_test                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "soil_test",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sample_date", sa.Date(), nullable=False),
        sa.Column("lab_name", sa.Text(), nullable=False),
        sa.Column("ph", sa.Numeric(3, 1), nullable=True),
        sa.Column("organic_matter_pct", sa.Numeric(4, 1), nullable=True),
        sa.Column("phosphorus_ppm", sa.Numeric(), nullable=True),
        sa.Column("potassium_ppm", sa.Numeric(), nullable=True),
        sa.Column("calcium_ppm", sa.Numeric(), nullable=True),
        sa.Column("magnesium_ppm", sa.Numeric(), nullable=True),
        sa.Column("sulfur_ppm", sa.Numeric(), nullable=True),
        sa.Column("iron_ppm", sa.Numeric(), nullable=True),
        sa.Column("manganese_ppm", sa.Numeric(), nullable=True),
        sa.Column("zinc_ppm", sa.Numeric(), nullable=True),
        sa.Column("copper_ppm", sa.Numeric(), nullable=True),
        sa.Column("boron_ppm", sa.Numeric(), nullable=True),
        sa.Column("cec", sa.Numeric(), nullable=True),
        sa.Column("base_saturation", JSONB(), nullable=True),
        sa.Column("lab_recommendations", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # weather_forecast                                                     #
    # ------------------------------------------------------------------ #
    op.create_table(
        "weather_forecast",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("forecast_for", sa.TIMESTAMP(timezone=True), nullable=False),
        # Hardcoded to America/Chicago — lawn is in Topeka, KS.
        # If multi-location support is ever added, move this to per-row
        # computation or denormalize the timezone onto lawn_profile.
        sa.Column(
            "forecast_for_day",
            sa.Date(),
            sa.Computed(
                "(forecast_for AT TIME ZONE 'America/Chicago')::date",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("temp_high_f", sa.Numeric(), nullable=True),
        sa.Column("temp_low_f", sa.Numeric(), nullable=True),
        sa.Column("precip_probability_pct", sa.Numeric(), nullable=True),
        sa.Column("precip_amount_in", sa.Numeric(), nullable=True),
        sa.Column("wind_mph", sa.Numeric(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "forecast_for_day", "source", name="weather_forecast_day_source_uniq"
        ),
    )

    # ------------------------------------------------------------------ #
    # reminder                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "reminder",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("reminder_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_treatment_id", sa.UUID(), nullable=True),
        sa.Column("completed_cultural_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reminder_type IN ('treatment','cultural','check','other')",
            name="reminder_reminder_type_check",
        ),
        sa.ForeignKeyConstraint(["completed_cultural_id"], ["cultural_practice.id"]),
        sa.ForeignKeyConstraint(["completed_treatment_id"], ["treatment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reminder")
    op.drop_table("weather_forecast")
    op.drop_table("soil_test")
    op.drop_table("cultural_practice")
    op.drop_table("treatment")
    op.drop_table("product")
    op.drop_table("equipment")
    op.drop_table("irrigation_zone")
    op.drop_table("lawn_profile")
