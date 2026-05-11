from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from lawn_api.models.constants import NON_AREA_RATE_UNITS, RATE_UNITS, TREATMENT_APPLICATORS


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


class TreatmentCreate(BaseModel):
    applied_at: datetime
    products: list[TreatmentProductIn]
    area_treated_sqft: int
    equipment_id: UUID | None = None
    applicator: Literal[*TREATMENT_APPLICATORS]
    weather_temp_f: float | None = None
    weather_wind_mph: float | None = None
    weather_conditions: str | None = None
    target: str | None = None
    notes: str | None = None

    @field_validator("products")
    @classmethod
    def validate_products(cls, v: list[TreatmentProductIn]) -> list[TreatmentProductIn]:
        """Ensure at least one product and at least one per-area rate unit."""
        if not v:
            raise ValueError("At least one product is required")

        # Check that at least one product uses a per-area rate unit
        has_per_area = any(prod.rate_unit not in NON_AREA_RATE_UNITS for prod in v)
        if not has_per_area:
            raise ValueError("At least one product must use a per-area rate unit")

        # Check for duplicate product_ids
        product_ids = {prod.product_id for prod in v}
        if len(product_ids) != len(v):
            raise ValueError("Duplicate products in tank mix")

        return v


class TreatmentPatch(BaseModel):
    applied_at: datetime | None = None
    products: list[TreatmentProductIn] | None = None
    area_treated_sqft: int | None = None
    equipment_id: UUID | None = None
    applicator: Literal[*TREATMENT_APPLICATORS] | None = None
    weather_temp_f: float | None = None
    weather_wind_mph: float | None = None
    weather_conditions: str | None = None
    target: str | None = None
    notes: str | None = None

    @field_validator("products")
    @classmethod
    def validate_products_patch(cls, v: list[TreatmentProductIn] | None) -> list[TreatmentProductIn] | None:
        """Ensure products (if provided) satisfy the same validation rules as TreatmentCreate."""
        if v is None:
            return None

        if not v:
            raise ValueError("At least one product is required")

        has_per_area = any(prod.rate_unit not in NON_AREA_RATE_UNITS for prod in v)
        if not has_per_area:
            raise ValueError("At least one product must use a per-area rate unit")

        product_ids = {prod.product_id for prod in v}
        if len(product_ids) != len(v):
            raise ValueError("Duplicate products in tank mix")

        return v


class TreatmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    applied_at: datetime
    products: list[TreatmentProductOut]
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
