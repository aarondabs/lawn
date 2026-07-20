from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lawn_api.db import get_db
from lawn_api.models.entities import (
    Equipment,
    FillProduct,
    Product,
    TankFill,
    Treatment,
    TreatmentProduct,
)
from lawn_api.schemas.treatment import (
    TankFillIn,
    TreatmentCreate,
    TreatmentOut,
    TreatmentPatch,
)
from lawn_api.services.inventory import (
    consume_treatment_inventory,
    restore_treatment_inventory,
)
from lawn_api.services.units import UnitConversionError, area_covered_sqft

router = APIRouter(prefix="/api/v1/treatments", tags=["treatments"])

# Loading options shared by every read path, so fills and their products are
# always present on the response model.
_LOAD_OPTIONS = (
    selectinload(Treatment.products),
    selectinload(Treatment.fills).selectinload(TankFill.products),
)


async def _load(db: AsyncSession, treatment_id: UUID) -> Treatment | None:
    return (
        await db.execute(select(Treatment).options(*_LOAD_OPTIONS).where(Treatment.id == treatment_id))
    ).scalar_one_or_none()


def _serialize(treatment: Treatment, warnings: list[dict[str, str]] | None = None) -> dict:
    """Build the response payload, adding values derived at serialization time.

    Effective rate is per 1,000 sq ft of the area that fill actually covered --
    not of the nominal lawn size, which a fill may deliberately exceed.
    """
    payload = {
        "id": treatment.id,
        "applied_at": treatment.applied_at,
        "application_method": treatment.application_method,
        "area_treated_sqft": treatment.area_treated_sqft,
        "equipment_id": treatment.equipment_id,
        "applicator": treatment.applicator,
        "weather_temp_f": treatment.weather_temp_f,
        "weather_wind_mph": treatment.weather_wind_mph,
        "weather_conditions": treatment.weather_conditions,
        "target": treatment.target,
        "notes": treatment.notes,
        "created_at": treatment.created_at,
        "updated_at": treatment.updated_at,
        "products": [
            {
                "product_id": tp.product_id,
                "rate_applied": tp.rate_applied,
                "rate_unit": tp.rate_unit,
                "position": tp.position,
                "notes": tp.notes,
            }
            for tp in treatment.products
        ],
        "fills": [],
        "inventory_warnings": warnings or [],
    }

    for fill in treatment.fills:
        area = Decimal(str(fill.area_covered_sqft))
        payload["fills"].append(
            {
                "id": fill.id,
                "fill_number": fill.fill_number,
                "total_mix_volume": fill.total_mix_volume,
                "total_mix_volume_unit": fill.total_mix_volume_unit,
                "calibrated_rate_snapshot": fill.calibrated_rate_snapshot,
                "calibrated_rate_unit_snapshot": fill.calibrated_rate_unit_snapshot,
                "area_covered_sqft": fill.area_covered_sqft,
                "notes": fill.notes,
                "products": [
                    {
                        "product_id": fp.product_id,
                        "amount_used": fp.amount_used,
                        "amount_used_unit": fp.amount_used_unit,
                        "notes": fp.notes,
                        "effective_rate_per_1000": (
                            float(Decimal(str(fp.amount_used)) / area * Decimal(1000)) if area > 0 else None
                        ),
                    }
                    for fp in fill.products
                ],
            }
        )

    return payload


async def _validate_products_exist(db: AsyncSession, product_ids: set[UUID]) -> None:
    for product_id in product_ids:
        if await db.get(Product, product_id) is None:
            raise HTTPException(status_code=400, detail=f"product_id {product_id} does not exist")


def _build_fills(fills: list[TankFillIn]) -> tuple[list[TankFill], int]:
    """Create TankFill rows with their derived area, and the total area covered.

    Fill numbers are assigned from list order -- the form appends fills in the
    order they were sprayed, so position is the ordering, not a user input.

    Rows are returned unattached; the caller associates them via the
    relationship so the FK is set on flush. The total is needed before the
    treatment row is inserted, since area_treated_sqft is NOT NULL.
    """
    built: list[TankFill] = []
    total_area = Decimal(0)

    for idx, fill in enumerate(fills, start=1):
        try:
            area = area_covered_sqft(
                Decimal(str(fill.total_mix_volume)),
                fill.total_mix_volume_unit,
                Decimal(str(fill.calibrated_rate_snapshot)),
                fill.calibrated_rate_unit_snapshot,
            )
        except UnitConversionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        total_area += area
        built.append(
            TankFill(
                fill_number=idx,
                total_mix_volume=fill.total_mix_volume,
                total_mix_volume_unit=fill.total_mix_volume_unit,
                calibrated_rate_snapshot=fill.calibrated_rate_snapshot,
                calibrated_rate_unit_snapshot=fill.calibrated_rate_unit_snapshot,
                area_covered_sqft=area,
                notes=fill.notes,
                products=[
                    FillProduct(
                        product_id=p.product_id,
                        amount_used=p.amount_used,
                        amount_used_unit=p.amount_used_unit,
                        notes=p.notes,
                    )
                    for p in fill.products
                ],
            )
        )

    return built, int(total_area)


@router.get("", response_model=list[TreatmentOut])
async def list_treatments(db: AsyncSession = Depends(get_db)) -> list[TreatmentOut]:
    rows = (await db.execute(select(Treatment).options(*_LOAD_OPTIONS).order_by(Treatment.applied_at.desc()))).scalars()
    return [_serialize(t) for t in rows]


@router.get("/{treatment_id}", response_model=TreatmentOut)
async def get_treatment(
    treatment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    treatment = await _load(db, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")
    return _serialize(treatment)


@router.post("", response_model=TreatmentOut, status_code=status.HTTP_201_CREATED)
async def create_treatment(
    payload: TreatmentCreate,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    product_ids = {p.product_id for p in payload.products}
    product_ids |= {fp.product_id for fill in payload.fills for fp in fill.products}
    await _validate_products_exist(db, product_ids)

    if payload.equipment_id is not None and await db.get(Equipment, payload.equipment_id) is None:
        raise HTTPException(status_code=400, detail="equipment_id does not exist")

    treatment_data = payload.model_dump(exclude={"products", "fills"})
    treatment = Treatment(**treatment_data)

    if payload.fills:
        fills, total_area = _build_fills(payload.fills)
        # Liquid area is the sum of what the fills actually covered. This can
        # exceed the lawn's nominal size when over-mixing, which is expected.
        # It must be set before the insert -- the column is NOT NULL.
        treatment.area_treated_sqft = total_area
        treatment.fills = fills

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

    await db.flush()
    # Reload with relationships eagerly loaded: the inventory service walks
    # treatment.products, and a lazy load there would fail under asyncio.
    created = await _load(db, treatment.id)
    assert created is not None
    warnings = await consume_treatment_inventory(db, created)
    await db.commit()

    refreshed = await _load(db, treatment.id)
    assert refreshed is not None
    return _serialize(refreshed, warnings)


@router.patch("/{treatment_id}", response_model=TreatmentOut)
async def patch_treatment(
    treatment_id: UUID,
    payload: TreatmentPatch,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    treatment = await _load(db, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")

    # Restore first, re-consume at the end. Diffing amounts across a changed set
    # of fills is error-prone; putting everything back and taking the new total
    # is correct even when products are added or dropped by the edit.
    warnings = await restore_treatment_inventory(db, treatment)

    updates = payload.model_dump(exclude_unset=True, exclude={"products", "fills"})

    if "equipment_id" in updates and updates["equipment_id"] is not None:
        if await db.get(Equipment, updates["equipment_id"]) is None:
            raise HTTPException(status_code=400, detail="equipment_id does not exist")

    for key, value in updates.items():
        setattr(treatment, key, value)

    if payload.products is not None:
        await _validate_products_exist(db, {p.product_id for p in payload.products})

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

    if payload.fills is not None:
        await _validate_products_exist(db, {fp.product_id for fill in payload.fills for fp in fill.products})
        # Fills are replaced wholesale rather than matched up: fill_number is
        # positional, so a reorder or an inserted fill would make identity
        # matching meaningless.
        for fill in list(treatment.fills):
            treatment.fills.remove(fill)
            await db.delete(fill)
        await db.flush()

        built, total_area = _build_fills(payload.fills)
        for fill in built:
            treatment.fills.append(fill)
        treatment.area_treated_sqft = total_area

    await db.flush()
    reloaded = await _load(db, treatment.id)
    assert reloaded is not None
    warnings += await consume_treatment_inventory(db, reloaded)
    await db.commit()

    updated = await _load(db, treatment.id)
    assert updated is not None
    return _serialize(updated, warnings)


@router.delete("/{treatment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treatment(
    treatment_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    treatment = await _load(db, treatment_id)
    if treatment is None:
        raise HTTPException(status_code=404, detail="Treatment not found")

    # Deleting a treatment means it did not happen -- put the product back.
    await restore_treatment_inventory(db, treatment)
    await db.delete(treatment)
    await db.commit()
