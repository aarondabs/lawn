from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import CulturalPractice, Reminder, Treatment
from lawn_api.schemas.reminder import (
    ReminderComplete,
    ReminderCreate,
    ReminderOut,
    ReminderPatch,
    ReminderSnooze,
)

router = APIRouter(prefix="/api/v1/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
async def list_reminders(
    completed: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ReminderOut]:
    q = select(Reminder).order_by(Reminder.due_date.asc())
    if completed is not None:
        q = q.where(Reminder.completed.is_(completed))
    rows = (await db.execute(q)).scalars()
    return list(rows)


@router.get("/{reminder_id}", response_model=ReminderOut)
async def get_reminder(
    reminder_id: UUID, db: AsyncSession = Depends(get_db)
) -> ReminderOut:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate, db: AsyncSession = Depends(get_db)
) -> ReminderOut:
    reminder = Reminder(**payload.model_dump())
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def patch_reminder(
    reminder_id: UUID,
    payload: ReminderPatch,
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, key, value)

    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.post("/{reminder_id}/complete", response_model=ReminderOut)
async def complete_reminder(
    reminder_id: UUID,
    payload: ReminderComplete,
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if reminder.completed:
        raise HTTPException(status_code=400, detail="Reminder is already completed")

    if payload.completed_treatment_id is not None:
        if await db.get(Treatment, payload.completed_treatment_id) is None:
            raise HTTPException(status_code=400, detail="completed_treatment_id does not exist")
    if payload.completed_cultural_id is not None:
        if await db.get(CulturalPractice, payload.completed_cultural_id) is None:
            raise HTTPException(status_code=400, detail="completed_cultural_id does not exist")

    reminder.completed = True
    reminder.completed_at = datetime.now(tz=timezone.utc)
    reminder.completed_treatment_id = payload.completed_treatment_id
    reminder.completed_cultural_id = payload.completed_cultural_id

    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.post("/{reminder_id}/snooze", response_model=ReminderOut)
async def snooze_reminder(
    reminder_id: UUID,
    payload: ReminderSnooze,
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if reminder.completed:
        raise HTTPException(status_code=400, detail="Cannot snooze a completed reminder")

    reminder.due_date = payload.new_due_date
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await db.delete(reminder)
    await db.commit()
