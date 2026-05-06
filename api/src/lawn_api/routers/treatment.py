from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import Equipment, Product, Treatment
from lawn_api.schemas.treatment import TreatmentCreate, TreatmentOut, TreatmentPatch

router = APIRouter(prefix="/api/v1/treatments", tags=["treatments"])


@router.get("", response_model=list[TreatmentOut])
async def list_treatments(db: AsyncSession = Depends(get_db)) -> list[TreatmentOut]:
    rows = (await db.execute(select(Treatment).order_by(Treatment.applied_at.desc()))).scalars()
    return list(rows)


@router.get("/{treatment_id}", response_model=TreatmentOut)
async def get_treatment(
    treatment_id: UUID, db: AsyncSession = Depends(get_db)
) -> TreatmentOut:
    treatment = await db.get(Treatment, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")
    return treatment


@router.post("", response_model=TreatmentOut, status_code=status.HTTP_201_CREATED)
async def create_treatment(
    payload: TreatmentCreate, db: AsyncSession = Depends(get_db)
) -> TreatmentOut:
    if await db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=400, detail="product_id does not exist")

    if payload.equipment_id is not None and await db.get(Equipment, payload.equipment_id) is None:
        raise HTTPException(status_code=400, detail="equipment_id does not exist")

    treatment = Treatment(**payload.model_dump())
    db.add(treatment)
    await db.commit()
    await db.refresh(treatment)
    return treatment


@router.patch("/{treatment_id}", response_model=TreatmentOut)
async def patch_treatment(
    treatment_id: UUID,
    payload: TreatmentPatch,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    treatment = await db.get(Treatment, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")

    updates = payload.model_dump(exclude_unset=True)
    if "product_id" in updates and await db.get(Product, updates["product_id"]) is None:
        raise HTTPException(status_code=400, detail="product_id does not exist")

    if "equipment_id" in updates and updates["equipment_id"] is not None:
        if await db.get(Equipment, updates["equipment_id"]) is None:
            raise HTTPException(status_code=400, detail="equipment_id does not exist")

    for key, value in updates.items():
        setattr(treatment, key, value)

    await db.commit()
    await db.refresh(treatment)
    return treatment


@router.delete("/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treatment(treatment_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    treatment = await db.get(Treatment, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")

    await db.delete(treatment)
    await db.commit()
