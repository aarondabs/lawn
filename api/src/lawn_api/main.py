from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import AsyncSessionLocal
from lawn_api.routers import (
    cultural_practice_router,
    equipment_router,
    irrigation_zone_router,
    lawn_profile_router,
    product_router,
    soil_test_router,
    treatment_router,
)

app = FastAPI(title="Lawn API")

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
