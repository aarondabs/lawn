from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lawn_api.models.constants import REMINDER_TYPES


class ReminderCreate(BaseModel):
    due_date: date
    reminder_type: Literal[*REMINDER_TYPES]
    description: str


class ReminderPatch(BaseModel):
    due_date: date | None = None
    reminder_type: Literal[*REMINDER_TYPES] | None = None
    description: str | None = None


class ReminderComplete(BaseModel):
    """Payload for completing a reminder."""

    completed_treatment_id: UUID | None = None
    completed_cultural_id: UUID | None = None


class ReminderSnooze(BaseModel):
    """Payload for snoozing a reminder to a new due date."""

    new_due_date: date


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    due_date: date
    reminder_type: str
    description: str
    completed: bool
    completed_at: datetime | None
    completed_treatment_id: UUID | None
    completed_cultural_id: UUID | None
    created_at: datetime
    updated_at: datetime
