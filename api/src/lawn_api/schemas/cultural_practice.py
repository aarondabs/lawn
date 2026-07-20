from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from lawn_api.models.constants import CULTURAL_PRACTICE_TYPES, MOW_ORIENTATIONS

MAX_CUT_HEIGHT_INCHES = 8.0


class MowDetails(BaseModel):
    """Structured mow fields stored in cultural_practice.details.

    Since details is JSONB there is no DB CHECK constraint, so this model is the
    only thing standing between a typo and a permanently unqueryable orientation.
    Extra keys are allowed so other practice types can share the column.
    """

    model_config = ConfigDict(extra="allow")

    cut_height_inches: float | None = None
    mow_orientation: Literal[*MOW_ORIENTATIONS] | None = None
    mow_orientation_other: str | None = None

    @field_validator("cut_height_inches")
    @classmethod
    def validate_cut_height(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if not 0 < v <= MAX_CUT_HEIGHT_INCHES:
            raise ValueError(f"cut_height_inches must be between 0 and {MAX_CUT_HEIGHT_INCHES}")
        # Deck heights are set in quarter-inch increments; anything else is a typo.
        if round(v * 4) != v * 4:
            raise ValueError("cut_height_inches must be a multiple of 0.25")
        return v


MOW_DETAIL_KEYS = frozenset(MowDetails.model_fields)


def validate_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate mow-specific keys in the details blob, if any are present.

    Keyed off the presence of mow fields rather than practice_type, so a PATCH
    that supplies details without practice_type is still checked.
    """
    if details is None or not MOW_DETAIL_KEYS.intersection(details):
        return details
    return MowDetails(**details).model_dump(exclude_none=True)


class CulturalPracticeCreate(BaseModel):
    performed_at: datetime
    practice_type: Literal[*CULTURAL_PRACTICE_TYPES]
    details: dict[str, Any] | None = None
    equipment_id: UUID | None = None
    notes: str | None = None

    @field_validator("details")
    @classmethod
    def check_details(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_details(v)


class CulturalPracticePatch(BaseModel):
    performed_at: datetime | None = None
    practice_type: Literal[*CULTURAL_PRACTICE_TYPES] | None = None
    details: dict[str, Any] | None = None
    equipment_id: UUID | None = None
    notes: str | None = None

    @field_validator("details")
    @classmethod
    def check_details(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return validate_details(v)


class CulturalPracticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    performed_at: datetime
    practice_type: str
    details: dict[str, Any] | None
    equipment_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
