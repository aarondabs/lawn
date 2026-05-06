from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lawn_api.models.constants import CULTURAL_PRACTICE_TYPES


class CulturalPracticeCreate(BaseModel):
    performed_at: datetime
    practice_type: Literal[*CULTURAL_PRACTICE_TYPES]
    details: dict[str, Any] | None = None
    equipment_id: UUID | None = None
    notes: str | None = None


class CulturalPracticePatch(BaseModel):
    performed_at: datetime | None = None
    practice_type: Literal[*CULTURAL_PRACTICE_TYPES] | None = None
    details: dict[str, Any] | None = None
    equipment_id: UUID | None = None
    notes: str | None = None


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
