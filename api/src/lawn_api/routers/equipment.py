from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import Equipment
from lawn_api.schemas.equipment import EquipmentCreate, EquipmentOut, EquipmentPatch

router = APIRouter(prefix="/api/v1/equipment", tags=["equipment"])


@router.get("", response_model=list[EquipmentOut])
async def list_equipment(db: AsyncSession = Depends(get_db)) -> list[EquipmentOut]:
    rows = (await db.execute(select(Equipment).order_by(Equipment.created_at.desc()))).scalars()
    return list(rows)


@router.get("/{equipment_id}", response_model=EquipmentOut)
async def get_equipment(
    equipment_id: UUID, db: AsyncSession = Depends(get_db)
) -> EquipmentOut:
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    payload: EquipmentCreate, db: AsyncSession = Depends(get_db)
) -> EquipmentOut:
    equipment = Equipment(**payload.model_dump())
    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)
    return equipment


@router.patch("/{equipment_id}", response_model=EquipmentOut)
async def patch_equipment(
    equipment_id: UUID,
    payload: EquipmentPatch,
    db: AsyncSession = Depends(get_db),
) -> EquipmentOut:
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(equipment, key, value)

    await db.commit()
    await db.refresh(equipment)
    return equipment


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(equipment_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")

    await db.delete(equipment)
    await db.commit()
