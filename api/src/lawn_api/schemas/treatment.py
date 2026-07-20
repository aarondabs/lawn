from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lawn_api.models.constants import (
    AMOUNT_UNITS,
    APPLICATION_METHODS,
    CALIBRATED_RATE_UNITS,
    MIX_VOLUME_UNITS,
    NON_AREA_RATE_UNITS,
    RATE_UNITS,
    TREATMENT_APPLICATORS,
)

# ---------------------------------------------------------------------------
# Granular path -- treatment_product (unchanged from Phase 1.5)
# ---------------------------------------------------------------------------


class TreatmentProductIn(BaseModel):
    """Tank mix product line item for treatment creation/update."""

    product_id: UUID
    rate_applied: float
    rate_unit: Literal[*RATE_UNITS]
    position: int | None = None
    notes: str | None = None


class TreatmentProductOut(BaseModel):
    """Tank mix product line item in response."""

    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    rate_applied: float
    rate_unit: str
    position: int | None
    notes: str | None


# ---------------------------------------------------------------------------
# Liquid path -- tank_fill / fill_product
# ---------------------------------------------------------------------------


class FillProductIn(BaseModel):
    """The measured amount of one product poured into one tank fill."""

    product_id: UUID
    amount_used: float = Field(gt=0)
    amount_used_unit: Literal[*AMOUNT_UNITS]
    notes: str | None = None


class FillProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    amount_used: float
    amount_used_unit: str
    notes: str | None
    # Derived at serialization: amount_used / area_covered_sqft * 1000.
    effective_rate_per_1000: float | None = None


class TankFillIn(BaseModel):
    """One sprayer tank. Area is derived, never supplied."""

    total_mix_volume: float = Field(gt=0)
    total_mix_volume_unit: Literal[*MIX_VOLUME_UNITS] = "gal"
    calibrated_rate_snapshot: float = Field(gt=0)
    calibrated_rate_unit_snapshot: Literal[*CALIBRATED_RATE_UNITS] = "gal_per_1000"
    products: list[FillProductIn]
    notes: str | None = None

    @model_validator(mode="after")
    def validate_products(self) -> "TankFillIn":
        if not self.products:
            raise ValueError("Each tank fill needs at least one product")
        product_ids = {p.product_id for p in self.products}
        if len(product_ids) != len(self.products):
            raise ValueError("Duplicate products within a single tank fill")
        return self


class TankFillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fill_number: int
    total_mix_volume: float
    total_mix_volume_unit: str
    calibrated_rate_snapshot: float
    calibrated_rate_unit_snapshot: str
    area_covered_sqft: float
    products: list[FillProductOut]
    notes: str | None


# ---------------------------------------------------------------------------
# Treatment
# ---------------------------------------------------------------------------


def _validate_method_payload(
    method: str | None,
    products: list[TreatmentProductIn] | None,
    fills: list[TankFillIn] | None,
    area_treated_sqft: int | None,
    *,
    partial: bool,
) -> None:
    """Enforce that a treatment carries the child rows its method implies.

    Granular records rates and needs an area to turn them into amounts. Liquid
    records amounts and mix volume, and derives its area -- supplying one would
    be meaningless, so it is rejected rather than silently ignored.
    """
    if method is None:
        # PATCH that does not touch the method: nothing method-specific to check.
        return

    if method == "liquid":
        if products:
            raise ValueError("A liquid treatment records tank fills, not per-treatment product rates")
        if area_treated_sqft is not None:
            raise ValueError(
                "area_treated_sqft is derived for liquid treatments "
                "(mix volume / calibrated rate) and must not be supplied"
            )
        if not partial and not fills:
            raise ValueError("A liquid treatment needs at least one tank fill")
        return

    # granular / other
    if fills:
        raise ValueError(f"Tank fills only apply to liquid treatments, not '{method}'")
    if not partial:
        if not products:
            raise ValueError("At least one product is required")
        if area_treated_sqft is None:
            raise ValueError("area_treated_sqft is required for a granular treatment")


def _validate_granular_products(products: list[TreatmentProductIn]) -> None:
    if not any(p.rate_unit not in NON_AREA_RATE_UNITS for p in products):
        raise ValueError("At least one product must use a per-area rate unit")
    if len({p.product_id for p in products}) != len(products):
        raise ValueError("Duplicate products in tank mix")


class TreatmentCreate(BaseModel):
    applied_at: datetime
    application_method: Literal[*APPLICATION_METHODS]
    # Granular only. Derived for liquid from the sum of fill areas.
    area_treated_sqft: int | None = None
    products: list[TreatmentProductIn] = Field(default_factory=list)
    fills: list[TankFillIn] = Field(default_factory=list)
    equipment_id: UUID | None = None
    applicator: Literal[*TREATMENT_APPLICATORS]
    weather_temp_f: float | None = None
    weather_wind_mph: float | None = None
    weather_conditions: str | None = None
    target: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "TreatmentCreate":
        _validate_method_payload(
            self.application_method,
            self.products,
            self.fills,
            self.area_treated_sqft,
            partial=False,
        )
        if self.products:
            _validate_granular_products(self.products)
        return self


class TreatmentPatch(BaseModel):
    applied_at: datetime | None = None
    application_method: Literal[*APPLICATION_METHODS] | None = None
    area_treated_sqft: int | None = None
    products: list[TreatmentProductIn] | None = None
    fills: list[TankFillIn] | None = None
    equipment_id: UUID | None = None
    applicator: Literal[*TREATMENT_APPLICATORS] | None = None
    weather_temp_f: float | None = None
    weather_wind_mph: float | None = None
    weather_conditions: str | None = None
    target: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "TreatmentPatch":
        _validate_method_payload(
            self.application_method,
            self.products,
            self.fills,
            self.area_treated_sqft,
            partial=True,
        )
        if self.products is not None:
            if not self.products:
                raise ValueError("At least one product is required")
            _validate_granular_products(self.products)
        if self.fills is not None and not self.fills:
            raise ValueError("A liquid treatment needs at least one tank fill")
        return self


class InventoryWarning(BaseModel):
    """A product whose inventory could not be adjusted, and why.

    Surfaced rather than swallowed: a skipped decrement means the recorded stock
    level is now wrong, and Aaron needs to know to reconcile it by hand.
    """

    product_id: UUID
    product_name: str
    message: str


class TreatmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    applied_at: datetime
    application_method: str
    products: list[TreatmentProductOut]
    fills: list[TankFillOut]
    area_treated_sqft: int
    equipment_id: UUID | None
    applicator: str
    weather_temp_f: float | None
    weather_wind_mph: float | None
    weather_conditions: str | None
    target: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # Populated on write responses only; never persisted.
    inventory_warnings: list[InventoryWarning] = Field(default_factory=list)
