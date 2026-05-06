from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lawn_api.models.constants import EQUIPMENT_TYPES


class EquipmentCreate(BaseModel):
    type: Literal[*EQUIPMENT_TYPES]
    make: str
    model: str
    calibration: dict[str, Any] | None = None
    last_calibration_date: date | None = None
    notes: str | None = None


class EquipmentPatch(BaseModel):
    type: Literal[*EQUIPMENT_TYPES] | None = None
    make: str | None = None
    model: str | None = None
    calibration: dict[str, Any] | None = None
    last_calibration_date: date | None = None
    notes: str | None = None


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    make: str
    model: str
    calibration: dict[str, Any] | None
    last_calibration_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
