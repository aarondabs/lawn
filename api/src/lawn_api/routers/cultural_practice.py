from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import CulturalPractice, Equipment
from lawn_api.schemas.cultural_practice import (
    CulturalPracticeCreate,
    CulturalPracticeOut,
    CulturalPracticePatch,
)

router = APIRouter(prefix="/api/v1/cultural-practices", tags=["cultural-practices"])


@router.get("", response_model=list[CulturalPracticeOut])
async def list_cultural_practices(
    db: AsyncSession = Depends(get_db),
) -> list[CulturalPracticeOut]:
    rows = (await db.execute(select(CulturalPractice).order_by(CulturalPractice.performed_at.desc()))).scalars()
    return list(rows)


@router.get("/{practice_id}", response_model=CulturalPracticeOut)
async def get_cultural_practice(practice_id: UUID, db: AsyncSession = Depends(get_db)) -> CulturalPracticeOut:
    practice = await db.get(CulturalPractice, practice_id)
    if practice is None:
        raise HTTPException(status_code=404, detail="Cultural practice not found")
    return practice


@router.post("", response_model=CulturalPracticeOut, status_code=status.HTTP_201_CREATED)
async def create_cultural_practice(
    payload: CulturalPracticeCreate, db: AsyncSession = Depends(get_db)
) -> CulturalPracticeOut:
    if payload.equipment_id is not None and await db.get(Equipment, payload.equipment_id) is None:
        raise HTTPException(status_code=400, detail="equipment_id does not exist")

    practice = CulturalPractice(**payload.model_dump())
    db.add(practice)
    await db.commit()
    await db.refresh(practice)
    return practice


@router.patch("/{practice_id}", response_model=CulturalPracticeOut)
async def patch_cultural_practice(
    practice_id: UUID,
    payload: CulturalPracticePatch,
    db: AsyncSession = Depends(get_db),
) -> CulturalPracticeOut:
    practice = await db.get(CulturalPractice, practice_id)
    if practice is None:
        raise HTTPException(status_code=404, detail="Cultural practice not found")

    updates = payload.model_dump(exclude_unset=True)
    if "equipment_id" in updates and updates["equipment_id"] is not None:
        if await db.get(Equipment, updates["equipment_id"]) is None:
            raise HTTPException(status_code=400, detail="equipment_id does not exist")

    for key, value in updates.items():
        setattr(practice, key, value)

    await db.commit()
    await db.refresh(practice)
    return practice


@router.delete("/{practice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cultural_practice(practice_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    practice = await db.get(CulturalPractice, practice_id)
    if practice is None:
        raise HTTPException(status_code=404, detail="Cultural practice not found")

    await db.delete(practice)
    await db.commit()
