"""
SQLAlchemy models for the Lawn Command Center.

Convention notes:
- Non-hypertable tables: UUID primary key (gen_random_uuid() server-side).
- Hypertable exceptions (see DATA_MODEL.md): weather_observation and
  irrigation_event use composite primary keys because TimescaleDB requires
  the partitioning column to be part of the primary key.
- Enum-like text columns use Postgres CHECK constraints (not native ENUM types)
  mirrored by pydantic Literals sourced from constants.py.
- All timestamps are UTC (timestamptz).
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from lawn_api.db import Base
from lawn_api.models.constants import (
    AMOUNT_UNITS,
    APPLICATION_METHODS,
    CALIBRATED_RATE_UNITS,
    CULTURAL_PRACTICE_TYPES,
    EQUIPMENT_TYPES,
    IRRIGATION_EVENT_SOURCES,
    IRRIGATION_HEAD_TYPES,
    IRRIGATION_SLOPES,
    IRRIGATION_SUN_EXPOSURES,
    IRRIGATION_ZONE_CATEGORIES,
    MIX_VOLUME_UNITS,
    PRODUCT_TYPES,
    RATE_UNITS,
    REMINDER_TYPES,
    SOIL_TYPES,
    TREATMENT_APPLICATORS,
    WATER_SOURCES,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sql_in(values: tuple[str, ...]) -> str:
    """Return a SQL IN-list string for a CHECK constraint."""
    return ", ".join(f"'{v}'" for v in values)


# ---------------------------------------------------------------------------
# lawn_profile - singleton row representing Aaron's lawn
# ---------------------------------------------------------------------------


class LawnProfile(Base):
    __tablename__ = "lawn_profile"
    __table_args__ = (
        UniqueConstraint("singleton_guard", name="lawn_profile_singleton"),
        CheckConstraint(
            f"soil_type IN ({_sql_in(SOIL_TYPES)})",
            name="lawn_profile_soil_type_check",
        ),
        CheckConstraint(
            f"water_source IN ({_sql_in(WATER_SOURCES)})",
            name="lawn_profile_water_source_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    # Singleton enforcement: only one row can have singleton_guard = true
    singleton_guard = Column(Boolean, nullable=False, server_default=text("true"))

    total_sqft = Column(Integer, nullable=False)
    grass_type = Column(Text, nullable=False, server_default="TTTF")
    establishment_date = Column(Date, nullable=True)
    target_mow_height_inches = Column(Numeric(3, 1), nullable=False)
    latitude = Column(Numeric(8, 5), nullable=False)
    longitude = Column(Numeric(9, 5), nullable=False)
    usda_zone = Column(Text, nullable=False, server_default="6a")
    climate_notes = Column(Text, nullable=True)
    soil_type = Column(Text, nullable=False)
    water_source = Column(Text, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ---------------------------------------------------------------------------
# irrigation_zone
# ---------------------------------------------------------------------------


class IrrigationZone(Base):
    __tablename__ = "irrigation_zone"
    __table_args__ = (
        UniqueConstraint("rachio_zone_id", name="irrigation_zone_rachio_id_uniq"),
        UniqueConstraint("zone_number", name="irrigation_zone_zone_number_uniq"),
        CheckConstraint(
            f"head_type IN ({_sql_in(IRRIGATION_HEAD_TYPES)})",
            name="irrigation_zone_head_type_check",
        ),
        CheckConstraint(
            f"sun_exposure IN ({_sql_in(IRRIGATION_SUN_EXPOSURES)})",
            name="irrigation_zone_sun_exposure_check",
        ),
        CheckConstraint(
            f"slope IN ({_sql_in(IRRIGATION_SLOPES)})",
            name="irrigation_zone_slope_check",
        ),
        CheckConstraint(
            f"soil_type_override IS NULL OR soil_type_override IN ({_sql_in(SOIL_TYPES)})",
            name="irrigation_zone_soil_type_override_check",
        ),
        CheckConstraint(
            f"zone_category IN ({_sql_in(IRRIGATION_ZONE_CATEGORIES)})",
            name="irrigation_zone_zone_category_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    rachio_zone_id = Column(Text, nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"))
    zone_category = Column(Text, nullable=False, server_default=text("'turf'"))
    zone_number = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    sqft = Column(Integer, nullable=True)
    head_type = Column(Text, nullable=False)
    nozzle_gpm = Column(Numeric(5, 2), nullable=True)
    precipitation_rate_in_per_hr = Column(Numeric(4, 2), nullable=True)
    sun_exposure = Column(Text, nullable=False)
    slope = Column(Text, nullable=False)
    soil_type_override = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    irrigation_events = relationship("IrrigationEvent", back_populates="zone")


# ---------------------------------------------------------------------------
# equipment
# ---------------------------------------------------------------------------


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint(
            f"type IN ({_sql_in(EQUIPMENT_TYPES)})",
            name="equipment_type_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    type = Column(Text, nullable=False)
    make = Column(Text, nullable=False)
    model = Column(Text, nullable=False)
    calibration = Column(JSONB(none_as_null=True), nullable=True)
    last_calibration_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    treatments = relationship("Treatment", back_populates="equipment")
    cultural_practices = relationship("CulturalPractice", back_populates="equipment")


# ---------------------------------------------------------------------------
# product
# ---------------------------------------------------------------------------


class Product(Base):
    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint(
            f"product_type IN ({_sql_in(PRODUCT_TYPES)})",
            name="product_product_type_check",
        ),
        CheckConstraint(
            f"label_rate_unit IN ({_sql_in(RATE_UNITS)})",
            name="product_label_rate_unit_check",
        ),
        CheckConstraint(
            # Inventory is a QUANTITY on the shelf, so it takes amount units. This
            # previously reused RATE_UNITS, which made "0 lb_per_1000 in stock" the
            # only expressible value -- meaningless, and unusable for decrement.
            f"current_inventory_unit IS NULL OR current_inventory_unit IN ({_sql_in(AMOUNT_UNITS)})",
            name="product_current_inventory_unit_check",
        ),
        CheckConstraint(
            f"max_annual_rate_unit IS NULL OR max_annual_rate_unit IN ({_sql_in(RATE_UNITS)})",
            name="product_max_annual_rate_unit_check",
        ),
        CheckConstraint(
            "reorder_threshold IS NULL OR reorder_threshold >= 0",
            name="product_reorder_threshold_non_negative",
        ),
        CheckConstraint(
            "preemergent_blocking_days IS NULL OR preemergent_blocking_days > 0",
            name="product_preemergent_blocking_days_positive",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False)
    manufacturer = Column(Text, nullable=False)
    product_type = Column(Text, nullable=False)
    active_ingredients = Column(JSONB(none_as_null=True), nullable=True)
    guaranteed_analysis = Column(JSONB(none_as_null=True), nullable=True)
    label_rate = Column(Numeric, nullable=False)
    label_rate_unit = Column(Text, nullable=False)
    reentry_interval_hours = Column(Integer, nullable=True)
    min_reapplication_days = Column(Integer, nullable=True)
    max_annual_rate = Column(Numeric, nullable=True)
    max_annual_rate_unit = Column(Text, nullable=True)
    current_inventory = Column(Numeric, nullable=True)
    current_inventory_unit = Column(Text, nullable=True)
    # Low-stock trigger. Shares current_inventory_unit rather than carrying its
    # own, so the two can never disagree.
    reorder_threshold = Column(Numeric, nullable=True)
    # How long this pre-emergent blocks seed germination. Only meaningful for
    # herbicide_pre; the guardrail falls back to a setting when unset.
    preemergent_blocking_days = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    treatment_products = relationship("TreatmentProduct", back_populates="product")
    fill_products = relationship("FillProduct", back_populates="product")


# ---------------------------------------------------------------------------
# treatment
# ---------------------------------------------------------------------------


class Treatment(Base):
    __tablename__ = "treatment"
    __table_args__ = (
        CheckConstraint(
            f"applicator IN ({_sql_in(TREATMENT_APPLICATORS)})",
            name="treatment_applicator_check",
        ),
        CheckConstraint(
            f"application_method IN ({_sql_in(APPLICATION_METHODS)})",
            name="treatment_application_method_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    applied_at = Column(TIMESTAMP(timezone=True), nullable=False)
    # Determines which child structure carries the product detail: 'granular'
    # uses treatment_product, 'liquid' uses tank_fill/fill_product.
    application_method = Column(Text, nullable=False)
    area_treated_sqft = Column(Integer, nullable=False)
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=True)
    applicator = Column(Text, nullable=False)
    weather_temp_f = Column(Numeric, nullable=True)
    weather_wind_mph = Column(Numeric, nullable=True)
    weather_conditions = Column(Text, nullable=True)
    target = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    equipment = relationship("Equipment", back_populates="treatments")
    products = relationship(
        "TreatmentProduct",
        back_populates="treatment",
        cascade="all, delete-orphan",
        order_by="TreatmentProduct.position",
    )
    fills = relationship(
        "TankFill",
        back_populates="treatment",
        cascade="all, delete-orphan",
        order_by="TankFill.fill_number",
    )
    reminders = relationship(
        "Reminder",
        foreign_keys="Reminder.completed_treatment_id",
        back_populates="completed_treatment",
    )


# ---------------------------------------------------------------------------
# treatment_product (join table for tank mixes)
# ---------------------------------------------------------------------------


class TreatmentProduct(Base):
    __tablename__ = "treatment_product"
    __table_args__ = (
        CheckConstraint(
            f"rate_unit IN ({_sql_in(RATE_UNITS)})",
            name="treatment_product_rate_unit_check",
        ),
    )

    treatment_id = Column(UUID(as_uuid=True), ForeignKey("treatment.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True)
    rate_applied = Column(Numeric, nullable=False)
    rate_unit = Column(Text, nullable=False)
    position = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    treatment = relationship("Treatment", back_populates="products")
    product = relationship("Product", back_populates="treatment_products")


# ---------------------------------------------------------------------------
# tank_fill - one sprayer tank for a liquid treatment
# ---------------------------------------------------------------------------


class TankFill(Base):
    """A single tank of mixed solution within a liquid treatment.

    Fills are first-class rather than summed into a flat total, because they
    genuinely differ -- running a couple of ounces short on the last fill is
    normal, and inventory decrement needs the real per-fill amounts.

    Area is derived (volume / calibrated rate), never entered. The calibrated
    rate is snapshotted so recalibrating the sprayer does not silently rewrite
    history, mirroring irrigation_event.precip_rate_in_per_hr_snapshot.
    """

    __tablename__ = "tank_fill"
    __table_args__ = (
        UniqueConstraint("treatment_id", "fill_number", name="tank_fill_treatment_fill_number_uniq"),
        CheckConstraint(
            f"total_mix_volume_unit IN ({_sql_in(MIX_VOLUME_UNITS)})",
            name="tank_fill_total_mix_volume_unit_check",
        ),
        CheckConstraint(
            f"calibrated_rate_unit_snapshot IN ({_sql_in(CALIBRATED_RATE_UNITS)})",
            name="tank_fill_calibrated_rate_unit_snapshot_check",
        ),
        CheckConstraint("total_mix_volume > 0", name="tank_fill_total_mix_volume_positive"),
        CheckConstraint("calibrated_rate_snapshot > 0", name="tank_fill_calibrated_rate_positive"),
        CheckConstraint("fill_number > 0", name="tank_fill_fill_number_positive"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    treatment_id = Column(UUID(as_uuid=True), ForeignKey("treatment.id", ondelete="CASCADE"), nullable=False)
    fill_number = Column(Integer, nullable=False)
    total_mix_volume = Column(Numeric, nullable=False)
    total_mix_volume_unit = Column(Text, nullable=False, server_default=text("'gal'"))
    calibrated_rate_snapshot = Column(Numeric, nullable=False)
    calibrated_rate_unit_snapshot = Column(Text, nullable=False, server_default=text("'gal_per_1000'"))
    # Computed in the service layer on write (see services/units.area_covered_sqft)
    # rather than as a GENERATED column, which could not handle unit conversion.
    area_covered_sqft = Column(Numeric, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    treatment = relationship("Treatment", back_populates="fills")
    products = relationship(
        "FillProduct",
        back_populates="fill",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# fill_product - what actually went into one tank fill
# ---------------------------------------------------------------------------


class FillProduct(Base):
    """Ground truth for a liquid application: the amount poured into a fill.

    Unlike treatment_product (which records a rate and derives the amount), this
    records the measured amount directly. Effective rate is derived from it and
    the fill's covered area.
    """

    __tablename__ = "fill_product"
    __table_args__ = (
        CheckConstraint(
            f"amount_used_unit IN ({_sql_in(AMOUNT_UNITS)})",
            name="fill_product_amount_used_unit_check",
        ),
        CheckConstraint("amount_used > 0", name="fill_product_amount_used_positive"),
        Index("ix_fill_product_product_id", "product_id"),
    )

    tank_fill_id = Column(UUID(as_uuid=True), ForeignKey("tank_fill.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id", ondelete="RESTRICT"), primary_key=True)
    amount_used = Column(Numeric, nullable=False)
    amount_used_unit = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    fill = relationship("TankFill", back_populates="products")
    product = relationship("Product", back_populates="fill_products")


# ---------------------------------------------------------------------------
# cultural_practice
# ---------------------------------------------------------------------------


class CulturalPractice(Base):
    __tablename__ = "cultural_practice"
    __table_args__ = (
        CheckConstraint(
            f"practice_type IN ({_sql_in(CULTURAL_PRACTICE_TYPES)})",
            name="cultural_practice_practice_type_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    performed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    practice_type = Column(Text, nullable=False)
    details = Column(JSONB(none_as_null=True), nullable=True)
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    equipment = relationship("Equipment", back_populates="cultural_practices")
    reminders = relationship(
        "Reminder",
        foreign_keys="Reminder.completed_cultural_id",
        back_populates="completed_cultural",
    )


# ---------------------------------------------------------------------------
# soil_test
# ---------------------------------------------------------------------------


class SoilTest(Base):
    __tablename__ = "soil_test"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    sample_date = Column(Date, nullable=False)
    lab_name = Column(Text, nullable=False)
    ph = Column(Numeric(3, 1), nullable=True)
    organic_matter_pct = Column(Numeric(4, 1), nullable=True)
    phosphorus_ppm = Column(Numeric, nullable=True)
    potassium_ppm = Column(Numeric, nullable=True)
    calcium_ppm = Column(Numeric, nullable=True)
    magnesium_ppm = Column(Numeric, nullable=True)
    sulfur_ppm = Column(Numeric, nullable=True)
    iron_ppm = Column(Numeric, nullable=True)
    manganese_ppm = Column(Numeric, nullable=True)
    zinc_ppm = Column(Numeric, nullable=True)
    copper_ppm = Column(Numeric, nullable=True)
    boron_ppm = Column(Numeric, nullable=True)
    cec = Column(Numeric, nullable=True)
    base_saturation = Column(JSONB(none_as_null=True), nullable=True)
    lab_recommendations = Column(Text, nullable=True)
    pdf_path = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# ---------------------------------------------------------------------------
# weather_forecast
# ---------------------------------------------------------------------------


class WeatherForecast(Base):
    __tablename__ = "weather_forecast"
    __table_args__ = (
        # Uniqueness is enforced on the derived calendar day (in Central Time)
        # rather than the raw timestamptz. See DATA_MODEL.md - Forecast overwrite.
        UniqueConstraint("forecast_for_day", "source", name="weather_forecast_day_source_uniq"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    forecast_for = Column(TIMESTAMP(timezone=True), nullable=False)
    # Hardcoded to America/Chicago - lawn is in Topeka, KS.
    # If multi-location support is ever added, move this to per-row
    # computation or denormalize the timezone onto lawn_profile.
    forecast_for_day = Column(
        Date,
        Computed(
            "(forecast_for AT TIME ZONE 'America/Chicago')::date",
            persisted=True,
        ),
        nullable=False,
    )
    fetched_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    source = Column(Text, nullable=False)
    temp_high_f = Column(Numeric, nullable=True)
    temp_low_f = Column(Numeric, nullable=True)
    precip_probability_pct = Column(Numeric, nullable=True)
    precip_amount_in = Column(Numeric, nullable=True)
    wind_mph = Column(Numeric, nullable=True)
    conditions = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# reminder
# ---------------------------------------------------------------------------


class Reminder(Base):
    __tablename__ = "reminder"
    __table_args__ = (
        CheckConstraint(
            f"reminder_type IN ({_sql_in(REMINDER_TYPES)})",
            name="reminder_reminder_type_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    due_date = Column(Date, nullable=False)
    reminder_type = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    completed = Column(Boolean, nullable=False, server_default=text("false"))
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_treatment_id = Column(UUID(as_uuid=True), ForeignKey("treatment.id"), nullable=True)
    completed_cultural_id = Column(UUID(as_uuid=True), ForeignKey("cultural_practice.id"), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    completed_treatment = relationship(
        "Treatment",
        foreign_keys=[completed_treatment_id],
        back_populates="reminders",
    )
    completed_cultural = relationship(
        "CulturalPractice",
        foreign_keys=[completed_cultural_id],
        back_populates="reminders",
    )


# ---------------------------------------------------------------------------
# weather_observation - TimescaleDB hypertable exception
# PK: (observed_at, source). No UUID.
# Partitioning column: observed_at.
# ---------------------------------------------------------------------------


class WeatherObservation(Base):
    __tablename__ = "weather_observation"
    # source is open-ended by design (openmeteo, personal weather station, etc.)
    # Validated by pydantic at the API edge; no DB CHECK constraint.

    observed_at = Column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    source = Column(Text, primary_key=True, nullable=False)
    temp_f = Column(Numeric, nullable=True)
    humidity_pct = Column(Numeric, nullable=True)
    dew_point_f = Column(Numeric, nullable=True)
    wind_mph = Column(Numeric, nullable=True)
    wind_gust_mph = Column(Numeric, nullable=True)
    precip_in = Column(Numeric, nullable=True)
    soil_temp_f = Column(Numeric, nullable=True)
    et0_in = Column(Numeric, nullable=True)
    gdd_base50 = Column(Numeric, nullable=True)


# ---------------------------------------------------------------------------
# irrigation_event - TimescaleDB hypertable exception
# PK: (started_at, zone_id). No UUID.
# Partitioning column: started_at.
# ---------------------------------------------------------------------------


class IrrigationEvent(Base):
    __tablename__ = "irrigation_event"
    __table_args__ = (
        # Partial unique index: rachio_event_id uniqueness enforced only when
        # non-null. Manual events have NULL and are not deduplicated this way.
        # TimescaleDB requires all unique indexes to include the partitioning column.
        # (rachio_event_id, started_at) is still an effective deduplication key because
        # a given Rachio event always has the same start time.
        Index(
            "irrigation_event_rachio_event_id_uniq",
            "rachio_event_id",
            "started_at",
            unique=True,
            postgresql_where=text("rachio_event_id IS NOT NULL"),
        ),
        CheckConstraint(
            f"source IN ({_sql_in(IRRIGATION_EVENT_SOURCES)})",
            name="irrigation_event_source_check",
        ),
    )

    started_at = Column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey("irrigation_zone.id"),
        primary_key=True,
        nullable=False,
    )
    rachio_event_id = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=False)
    # Snapshot the zone's precip rate at insert time so historical inches_applied
    # reflects the calibration in effect then, not the current calibration.
    precip_rate_in_per_hr_snapshot = Column(Numeric(4, 2), nullable=False)
    # Generated from local columns only - Postgres generated columns cannot
    # reference other tables, hence the snapshot pattern above.
    inches_applied = Column(
        Numeric(6, 3),
        Computed(
            "duration_seconds / 3600.0 * precip_rate_in_per_hr_snapshot",
            persisted=True,
        ),
        nullable=False,
    )
    source = Column(Text, nullable=False)
    skipped = Column(Boolean, nullable=False, server_default=text("false"))
    skip_reason = Column(Text, nullable=True)

    zone = relationship("IrrigationZone", back_populates="irrigation_events")
