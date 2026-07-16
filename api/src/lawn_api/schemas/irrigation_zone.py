from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lawn_api.models.constants import (
    IRRIGATION_HEAD_TYPES,
    IRRIGATION_SLOPES,
    IRRIGATION_SUN_EXPOSURES,
    IRRIGATION_ZONE_CATEGORIES,
    SOIL_TYPES,
)


class IrrigationZoneCreate(BaseModel):
    rachio_zone_id: str | None = None
    is_enabled: bool = True
    zone_category: Literal[*IRRIGATION_ZONE_CATEGORIES] = "turf"
    zone_number: int
    name: str
    sqft: int | None = None
    head_type: Literal[*IRRIGATION_HEAD_TYPES]
    nozzle_gpm: float | None = None
    precipitation_rate_in_per_hr: float | None = None
    sun_exposure: Literal[*IRRIGATION_SUN_EXPOSURES]
    slope: Literal[*IRRIGATION_SLOPES]
    soil_type_override: Literal[*SOIL_TYPES] | None = None
    notes: str | None = None


class IrrigationZonePatch(BaseModel):
    rachio_zone_id: str | None = None
    is_enabled: bool | None = None
    zone_category: Literal[*IRRIGATION_ZONE_CATEGORIES] | None = None
    zone_number: int | None = None
    name: str | None = None
    sqft: int | None = None
    head_type: Literal[*IRRIGATION_HEAD_TYPES] | None = None
    nozzle_gpm: float | None = None
    precipitation_rate_in_per_hr: float | None = None
    sun_exposure: Literal[*IRRIGATION_SUN_EXPOSURES] | None = None
    slope: Literal[*IRRIGATION_SLOPES] | None = None
    soil_type_override: Literal[*SOIL_TYPES] | None = None
    notes: str | None = None


class IrrigationZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rachio_zone_id: str | None
    is_enabled: bool
    zone_category: str
    zone_number: int
    name: str
    sqft: int | None
    head_type: str
    nozzle_gpm: float | None
    precipitation_rate_in_per_hr: float | None
    sun_exposure: str
    slope: str
    soil_type_override: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
