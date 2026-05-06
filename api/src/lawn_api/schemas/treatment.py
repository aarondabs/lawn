from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lawn_api.models.constants import PRODUCT_UNITS, TREATMENT_APPLICATORS


class TreatmentCreate(BaseModel):
    applied_at: datetime
    product_id: UUID
    rate_applied: float
    rate_unit: Literal[*PRODUCT_UNITS]
    area_treated_sqft: int
    equipment_id: UUID | None = None
    applicator: Literal[*TREATMENT_APPLICATORS]
    weather_temp_f: float | None = None
    weather_wind_mph: float | None = None
    weather_conditions: str | None = None
    target: str | None = None
    notes: str | None = None


class TreatmentPatch(BaseModel):
    applied_at: datetime | None = None
    product_id: UUID | None = None
    rate_applied: float | None = None
    rate_unit: Literal[*PRODUCT_UNITS] | None = None
    area_treated_sqft: int | None = None
    equipment_id: UUID | None = None
    applicator: Literal[*TREATMENT_APPLICATORS] | None = None
    weather_temp_f: float | None = None
    weather_wind_mph: float | None = None
    weather_conditions: str | None = None
    target: str | None = None
    notes: str | None = None


class TreatmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    applied_at: datetime
    product_id: UUID
    rate_applied: float
    rate_unit: str
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
