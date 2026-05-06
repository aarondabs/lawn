from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import LawnProfile
from lawn_api.schemas.lawn_profile import LawnProfileOut, LawnProfilePatch, LawnProfileUpsert

router = APIRouter(prefix="/api/v1/lawn-profile", tags=["lawn-profile"])


@router.get("", response_model=LawnProfileOut)
async def get_lawn_profile(db: AsyncSession = Depends(get_db)) -> LawnProfileOut:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Lawn profile not found")
    return profile


@router.post("", response_model=LawnProfileOut)
async def upsert_lawn_profile(
    payload: LawnProfileUpsert, db: AsyncSession = Depends(get_db)
) -> LawnProfileOut:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    if profile is None:
        profile = LawnProfile(**payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.patch("", response_model=LawnProfileOut)
async def patch_lawn_profile(
    payload: LawnProfilePatch, db: AsyncSession = Depends(get_db)
) -> LawnProfileOut:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Lawn profile not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lawn_profile(db: AsyncSession = Depends(get_db)) -> None:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Lawn profile not found")

    await db.delete(profile)
    await db.commit()
