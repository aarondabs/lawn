import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import AsyncSessionLocal
from lawn_api.routers import (
    admin_router,
    cultural_practice_router,
    dashboard_router,
    equipment_router,
    irrigation_zone_router,
    lawn_profile_router,
    product_router,
    rachio_router,
    soil_test_router,
    treatment_router,
)
from lawn_api.services.rachio import poll_rachio_events, should_schedule_rachio_polling
from lawn_api.services.weather import refresh_weather

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def scheduled_weather_refresh() -> None:
        try:
            async with AsyncSessionLocal() as session:
                await refresh_weather(session)
        except Exception:
            logger.exception("Scheduled weather refresh failed")

    async def scheduled_rachio_poll() -> None:
        try:
            async with AsyncSessionLocal() as session:
                await poll_rachio_events(session)
        except Exception:
            logger.exception("Scheduled Rachio polling failed")

    scheduler.add_job(
        scheduled_weather_refresh,
        trigger="interval",
        hours=6,
        id="weather-refresh",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

    async with AsyncSessionLocal() as session:
        if await should_schedule_rachio_polling(session):
            scheduler.add_job(
                scheduled_rachio_poll,
                trigger="interval",
                hours=1,
                id="rachio-poll",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )

    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)

app = FastAPI(title="Lawn API", lifespan=lifespan)

app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(rachio_router)
app.include_router(lawn_profile_router)
app.include_router(irrigation_zone_router)
app.include_router(equipment_router)
app.include_router(product_router)
app.include_router(cultural_practice_router)
app.include_router(treatment_router)
app.include_router(soil_test_router)


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}
