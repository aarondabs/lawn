from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import LawnProfile
from lawn_api.services import export as export_service

router = APIRouter(prefix="/api/v1/export", tags=["export"])


def _csv_response(rows: list[dict], fieldnames: list[str], filename: str) -> Response:
    body = export_service.rows_to_csv(rows, fieldnames)
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/treatments.csv")
async def export_treatments(db: AsyncSession = Depends(get_db)) -> Response:
    rows = await export_service.treatment_rows(db)
    return _csv_response(rows, export_service.TREATMENT_FIELDS, "treatments.csv")


@router.get("/cultural-practices.csv")
async def export_cultural(db: AsyncSession = Depends(get_db)) -> Response:
    rows = await export_service.cultural_rows(db)
    return _csv_response(rows, export_service.CULTURAL_FIELDS, "cultural-practices.csv")


@router.get("/irrigation-events.csv")
async def export_irrigation(db: AsyncSession = Depends(get_db)) -> Response:
    rows = await export_service.irrigation_rows(db)
    return _csv_response(rows, export_service.IRRIGATION_FIELDS, "irrigation-events.csv")


@router.get("/products.csv")
async def export_products(db: AsyncSession = Depends(get_db)) -> Response:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    rows = await export_service.product_rows(db, profile.total_sqft if profile else None)
    return _csv_response(rows, export_service.PRODUCT_FIELDS, "products.csv")


@router.get("/soil-tests.csv")
async def export_soil_tests(db: AsyncSession = Depends(get_db)) -> Response:
    rows = await export_service.soil_test_rows(db)
    return _csv_response(rows, export_service.SOIL_TEST_FIELDS, "soil-tests.csv")


@router.get("/weather-daily.csv")
async def export_weather(db: AsyncSession = Depends(get_db)) -> Response:
    rows = await export_service.weather_daily_rows(db)
    return _csv_response(rows, export_service.WEATHER_FIELDS, "weather-daily.csv")
