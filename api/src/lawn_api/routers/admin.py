from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.services.reminder_rules import evaluate_reminder_rules
from lawn_api.services.weather import refresh_weather

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/refresh-weather")
async def refresh_weather_endpoint(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await refresh_weather(db)


@router.post("/evaluate-reminders")
async def evaluate_reminders_endpoint(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Run the reminder rules on demand (the scheduler also runs them daily)."""
    created = await evaluate_reminder_rules(db)
    return {
        "status": "ok",
        "created": [{"type": r.reminder_type, "description": r.description} for r in created],
    }
