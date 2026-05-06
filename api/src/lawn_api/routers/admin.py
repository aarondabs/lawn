from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.services.weather import refresh_weather

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/refresh-weather")
async def refresh_weather_endpoint(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await refresh_weather(db)
