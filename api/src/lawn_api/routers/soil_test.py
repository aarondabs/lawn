from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import SoilTest
from lawn_api.schemas.soil_test import SoilTestCreate, SoilTestOut, SoilTestPatch

router = APIRouter(prefix="/api/v1/soil-tests", tags=["soil-tests"])


@router.get("", response_model=list[SoilTestOut])
async def list_soil_tests(db: AsyncSession = Depends(get_db)) -> list[SoilTestOut]:
    rows = (await db.execute(select(SoilTest).order_by(SoilTest.sample_date.desc()))).scalars()
    return list(rows)


@router.get("/{soil_test_id}", response_model=SoilTestOut)
async def get_soil_test(soil_test_id: UUID, db: AsyncSession = Depends(get_db)) -> SoilTestOut:
    soil_test = await db.get(SoilTest, soil_test_id)
    if soil_test is None:
        raise HTTPException(status_code=404, detail="Soil test not found")
    return soil_test


@router.post("", response_model=SoilTestOut, status_code=status.HTTP_201_CREATED)
async def create_soil_test(payload: SoilTestCreate, db: AsyncSession = Depends(get_db)) -> SoilTestOut:
    soil_test = SoilTest(**payload.model_dump())
    db.add(soil_test)
    await db.commit()
    await db.refresh(soil_test)
    return soil_test


@router.patch("/{soil_test_id}", response_model=SoilTestOut)
async def patch_soil_test(
    soil_test_id: UUID,
    payload: SoilTestPatch,
    db: AsyncSession = Depends(get_db),
) -> SoilTestOut:
    soil_test = await db.get(SoilTest, soil_test_id)
    if soil_test is None:
        raise HTTPException(status_code=404, detail="Soil test not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(soil_test, key, value)

    await db.commit()
    await db.refresh(soil_test)
    return soil_test


@router.delete("/{soil_test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_soil_test(soil_test_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    soil_test = await db.get(SoilTest, soil_test_id)
    if soil_test is None:
        raise HTTPException(status_code=404, detail="Soil test not found")

    await db.delete(soil_test)
    await db.commit()
