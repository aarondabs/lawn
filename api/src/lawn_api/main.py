import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlalchemy import text

from lawn_api.db import AsyncSessionLocal
from lawn_api.routers import (
    admin_router,
    assistant_router,
    cultural_practice_router,
    dashboard_router,
    equipment_router,
    export_router,
    guardrail_router,
    irrigation_zone_router,
    lawn_profile_router,
    product_router,
    rachio_router,
    reminder_router,
    soil_test_router,
    treatment_router,
)
from lawn_api.services.scheduler_jobs import register_jobs

# Uvicorn configures only its own loggers; without a root handler at INFO the
# app's operational logging — notably the per-call LLM token usage that cost
# monitoring depends on — is silently dropped. No-op if a handler exists.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = AsyncIOScheduler(timezone="UTC")
    await register_jobs(scheduler)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Lawn API", lifespan=lifespan)

app.include_router(admin_router)
app.include_router(assistant_router)
app.include_router(dashboard_router)
app.include_router(rachio_router)
app.include_router(lawn_profile_router)
app.include_router(irrigation_zone_router)
app.include_router(equipment_router)
app.include_router(export_router)
app.include_router(guardrail_router)
app.include_router(product_router)
app.include_router(cultural_practice_router)
app.include_router(treatment_router)
app.include_router(soil_test_router)
app.include_router(reminder_router)


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}
