from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import IrrigationZone
from lawn_api.schemas.irrigation_zone import (
    IrrigationZoneCreate,
    IrrigationZoneOut,
    IrrigationZonePatch,
)

router = APIRouter(prefix="/api/v1/irrigation-zones", tags=["irrigation-zones"])


@router.get("", response_model=list[IrrigationZoneOut])
async def list_irrigation_zones(
    include_disabled: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> list[IrrigationZoneOut]:
    stmt = select(IrrigationZone)
    if not include_disabled:
        stmt = stmt.where(IrrigationZone.is_enabled.is_(True))
    rows = (await db.execute(stmt.order_by(IrrigationZone.zone_number))).scalars()
    return list(rows)


@router.get("/{zone_id}", response_model=IrrigationZoneOut)
async def get_irrigation_zone(zone_id: UUID, db: AsyncSession = Depends(get_db)) -> IrrigationZoneOut:
    zone = await db.get(IrrigationZone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Irrigation zone not found")
    return zone


@router.post("", response_model=IrrigationZoneOut, status_code=status.HTTP_201_CREATED)
async def create_irrigation_zone(
    payload: IrrigationZoneCreate, db: AsyncSession = Depends(get_db)
) -> IrrigationZoneOut:
    zone = IrrigationZone(**payload.model_dump())
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.patch("/{zone_id}", response_model=IrrigationZoneOut)
async def patch_irrigation_zone(
    zone_id: UUID,
    payload: IrrigationZonePatch,
    db: AsyncSession = Depends(get_db),
) -> IrrigationZoneOut:
    zone = await db.get(IrrigationZone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Irrigation zone not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(zone, key, value)

    await db.commit()
    await db.refresh(zone)
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_irrigation_zone(zone_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    zone = await db.get(IrrigationZone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Irrigation zone not found")

    await db.delete(zone)
    await db.commit()
