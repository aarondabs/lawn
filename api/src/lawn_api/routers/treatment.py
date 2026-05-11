from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lawn_api.db import get_db
from lawn_api.models.entities import Equipment, Product, Treatment, TreatmentProduct
from lawn_api.schemas.treatment import TreatmentCreate, TreatmentOut, TreatmentPatch

router = APIRouter(prefix="/api/v1/treatments", tags=["treatments"])


@router.get("", response_model=list[TreatmentOut])
async def list_treatments(db: AsyncSession = Depends(get_db)) -> list[TreatmentOut]:
    rows = (
        await db.execute(
            select(Treatment)
            .options(selectinload(Treatment.products))
            .order_by(Treatment.applied_at.desc())
        )
    ).scalars()
    return list(rows)


@router.get("/{treatment_id}", response_model=TreatmentOut)
async def get_treatment(
    treatment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    treatment = (
        await db.execute(
            select(Treatment)
            .options(selectinload(Treatment.products))
            .where(Treatment.id == treatment_id)
        )
    ).scalar_one_or_none()
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")
    return treatment


@router.post("", response_model=TreatmentOut, status_code=status.HTTP_201_CREATED)
async def create_treatment(
    payload: TreatmentCreate,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    for prod in payload.products:
        if await db.get(Product, prod.product_id) is None:
            raise HTTPException(status_code=400, detail=f"product_id {prod.product_id} does not exist")

    if payload.equipment_id is not None and await db.get(Equipment, payload.equipment_id) is None:
        raise HTTPException(status_code=400, detail="equipment_id does not exist")

    treatment_data = payload.model_dump(exclude={"products"})
    treatment = Treatment(**treatment_data)
    db.add(treatment)
    await db.flush()

    for idx, prod in enumerate(payload.products):
        db.add(
            TreatmentProduct(
                treatment_id=treatment.id,
                product_id=prod.product_id,
                rate_applied=prod.rate_applied,
                rate_unit=prod.rate_unit,
                position=prod.position if prod.position is not None else idx,
                notes=prod.notes,
            )
        )

    await db.commit()

    created = (
        await db.execute(
            select(Treatment)
            .options(selectinload(Treatment.products))
            .where(Treatment.id == treatment.id)
        )
    ).scalar_one()
    return created


@router.patch("/{treatment_id}", response_model=TreatmentOut)
async def patch_treatment(
    treatment_id: UUID,
    payload: TreatmentPatch,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    treatment = (
        await db.execute(
            select(Treatment)
            .options(selectinload(Treatment.products))
            .where(Treatment.id == treatment_id)
        )
    ).scalar_one_or_none()
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")

    updates = payload.model_dump(exclude_unset=True, exclude={"products"})

    if "equipment_id" in updates and updates["equipment_id"] is not None:
        if await db.get(Equipment, updates["equipment_id"]) is None:
            raise HTTPException(status_code=400, detail="equipment_id does not exist")

    for key, value in updates.items():
        setattr(treatment, key, value)

    if payload.products is not None:
        for prod in payload.products:
            if await db.get(Product, prod.product_id) is None:
                raise HTTPException(status_code=400, detail=f"product_id {prod.product_id} does not exist")

        existing_by_product_id = {tp.product_id: tp for tp in treatment.products}
        incoming_product_ids = {prod.product_id for prod in payload.products}

        for tp in list(treatment.products):
            if tp.product_id not in incoming_product_ids:
                treatment.products.remove(tp)
                await db.delete(tp)

        for idx, prod in enumerate(payload.products):
            position = prod.position if prod.position is not None else idx
            current = existing_by_product_id.get(prod.product_id)

            if current is None:
                treatment.products.append(
                    TreatmentProduct(
                        treatment_id=treatment.id,
                        product_id=prod.product_id,
                        rate_applied=prod.rate_applied,
                        rate_unit=prod.rate_unit,
                        position=position,
                        notes=prod.notes,
                    )
                )
                continue

            current.rate_applied = prod.rate_applied
            current.rate_unit = prod.rate_unit
            current.position = position
            current.notes = prod.notes

    await db.commit()

    updated = (
        await db.execute(
            select(Treatment)
            .options(selectinload(Treatment.products))
            .where(Treatment.id == treatment.id)
        )
    ).scalar_one()
    return updated


@router.delete("/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treatment(
    treatment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    treatment = await db.get(Treatment, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")

    await db.delete(treatment)
    await db.commit()
