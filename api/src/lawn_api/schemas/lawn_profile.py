from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lawn_api.models.constants import SOIL_TYPES, WATER_SOURCES


class LawnProfileUpsert(BaseModel):
    total_sqft: int
    grass_type: str = "TTTF"
    establishment_date: date | None = None
    target_mow_height_inches: float
    latitude: float
    longitude: float
    usda_zone: str = "6a"
    climate_notes: str | None = None
    soil_type: Literal[*SOIL_TYPES]
    water_source: Literal[*WATER_SOURCES]


class LawnProfilePatch(BaseModel):
    total_sqft: int | None = None
    grass_type: str | None = None
    establishment_date: date | None = None
    target_mow_height_inches: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    usda_zone: str | None = None
    climate_notes: str | None = None
    soil_type: Literal[*SOIL_TYPES] | None = None
    water_source: Literal[*WATER_SOURCES] | None = None


class LawnProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    total_sqft: int
    grass_type: str
    establishment_date: date | None
    target_mow_height_inches: float
    latitude: float
    longitude: float
    usda_zone: str
    climate_notes: str | None
    soil_type: str
    water_source: str
    created_at: datetime
    updated_at: datetime
