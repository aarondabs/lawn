from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lawn_api.models.constants import CALIBRATED_RATE_UNITS, EQUIPMENT_TYPES

# Keys the sprayer calibration blob is expected to carry. Anything else is left
# alone -- other equipment types may use `calibration` for their own purposes.
SPRAYER_CALIBRATION_KEYS = frozenset(
    {"application_rate", "application_rate_unit", "nozzle_count", "pressure_psi"}
)


class SprayerCalibration(BaseModel):
    """Sprayer output, stored in equipment.calibration (JSONB).

    `application_rate` is the value the liquid treatment form consumes: it turns
    a tank volume into the area that tank covers. Validated here because JSONB
    carries no CHECK constraint, and a bad rate would silently skew every
    derived area.
    """

    model_config = ConfigDict(extra="allow")

    application_rate: float | None = Field(default=None, gt=0)
    application_rate_unit: Literal[*CALIBRATED_RATE_UNITS] | None = None
    nozzle_count: int | None = Field(default=None, gt=0)
    pressure_psi: float | None = Field(default=None, gt=0)


def validate_calibration(value: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate the sprayer keys in a calibration blob, when any are present."""
    if value is None or not SPRAYER_CALIBRATION_KEYS.intersection(value):
        return value

    parsed = SprayerCalibration(**value)
    if parsed.application_rate is not None and parsed.application_rate_unit is None:
        raise ValueError("application_rate_unit is required when application_rate is set")
    return parsed.model_dump(exclude_none=True)


class EquipmentCreate(BaseModel):
    type: Literal[*EQUIPMENT_TYPES]
    make: str
    model: str
    calibration: dict[str, Any] | None = None
    last_calibration_date: date | None = None
    notes: str | None = None

    @field_validator("calibration")
    @classmethod
    def check_calibration(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_calibration(v)


class EquipmentPatch(BaseModel):
    type: Literal[*EQUIPMENT_TYPES] | None = None
    make: str | None = None
    model: str | None = None
    calibration: dict[str, Any] | None = None
    last_calibration_date: date | None = None
    notes: str | None = None

    @field_validator("calibration")
    @classmethod
    def check_calibration(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_calibration(v)


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
