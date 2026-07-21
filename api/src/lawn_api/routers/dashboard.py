from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lawn_api.db import get_db
from lawn_api.models.entities import (
    CulturalPractice,
    IrrigationEvent,
    IrrigationZone,
    Reminder,
    SoilTest,
    Treatment,
    TreatmentProduct,
    WeatherForecast,
    WeatherObservation,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _num(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    now_utc = datetime.now(tz=ZoneInfo("UTC"))
    central = ZoneInfo("America/Chicago")
    today_central = now_utc.astimezone(central).date()
    seven_days_ago = now_utc - timedelta(days=7)

    latest_observation = (
        await db.execute(select(WeatherObservation).order_by(WeatherObservation.observed_at.desc()).limit(1))
    ).scalar_one_or_none()

    today_forecast = (
        await db.execute(
            select(WeatherForecast)
            .where(WeatherForecast.forecast_for_day == today_central)
            .order_by(WeatherForecast.fetched_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    seven_days_out = today_central + timedelta(days=6)
    upcoming_forecast_rows = (
        (
            await db.execute(
                select(WeatherForecast)
                .where(
                    and_(
                        WeatherForecast.forecast_for_day >= today_central,
                        WeatherForecast.forecast_for_day <= seven_days_out,
                    )
                )
                .order_by(
                    WeatherForecast.forecast_for_day.asc(),
                    WeatherForecast.fetched_at.desc(),
                )
            )
        )
        .scalars()
        .all()
    )

    # Keep one row per day (latest fetched), regardless of source.
    forecast_by_day: dict[object, WeatherForecast] = {}
    for row in upcoming_forecast_rows:
        if row.forecast_for_day not in forecast_by_day:
            forecast_by_day[row.forecast_for_day] = row

    next_7_days_forecast = [
        {
            "date": day.isoformat(),
            "temp_high_f": _num(forecast_by_day.get(day).temp_high_f) if forecast_by_day.get(day) else None,
            "temp_low_f": _num(forecast_by_day.get(day).temp_low_f) if forecast_by_day.get(day) else None,
            "precip_probability_pct": (
                _num(forecast_by_day.get(day).precip_probability_pct) if forecast_by_day.get(day) else None
            ),
            "precip_amount_in": _num(forecast_by_day.get(day).precip_amount_in) if forecast_by_day.get(day) else None,
            "wind_mph": _num(forecast_by_day.get(day).wind_mph) if forecast_by_day.get(day) else None,
            "conditions": forecast_by_day.get(day).conditions if forecast_by_day.get(day) else None,
        }
        for day in [today_central + timedelta(days=offset) for offset in range(7)]
    ]

    forecast_rainfall_7d_in = sum(day["precip_amount_in"] or 0 for day in next_7_days_forecast)

    rainfall_7d = (
        await db.execute(
            select(func.coalesce(func.sum(WeatherObservation.precip_in), 0)).where(
                WeatherObservation.observed_at >= seven_days_ago
            )
        )
    ).scalar_one()

    irrigation_rows = (
        await db.execute(
            select(
                IrrigationZone.id,
                IrrigationZone.name,
                IrrigationZone.zone_number,
                IrrigationZone.sqft,
                IrrigationZone.is_enabled,
                IrrigationZone.zone_category,
                func.coalesce(func.sum(IrrigationEvent.inches_applied), 0).label("inches"),
            )
            .outerjoin(
                IrrigationEvent,
                and_(
                    IrrigationEvent.zone_id == IrrigationZone.id,
                    IrrigationEvent.started_at >= seven_days_ago,
                ),
            )
            .group_by(
                IrrigationZone.id,
                IrrigationZone.name,
                IrrigationZone.zone_number,
                IrrigationZone.sqft,
                IrrigationZone.is_enabled,
                IrrigationZone.zone_category,
            )
            .where(IrrigationZone.is_enabled.is_(True))
            .order_by(IrrigationZone.zone_number.asc())
        )
    ).all()

    last_treatment_obj = (
        await db.execute(
            select(Treatment)
            .options(selectinload(Treatment.products).selectinload(TreatmentProduct.product))
            .order_by(Treatment.applied_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    cultural_rows = (
        (
            await db.execute(
                select(CulturalPractice).order_by(
                    CulturalPractice.practice_type.asc(), CulturalPractice.performed_at.desc()
                )
            )
        )
        .scalars()
        .all()
    )
    latest_cultural_by_type: dict[str, CulturalPractice] = {}
    for practice in cultural_rows:
        if practice.practice_type not in latest_cultural_by_type:
            latest_cultural_by_type[practice.practice_type] = practice

    latest_soil_test = (
        await db.execute(select(SoilTest).order_by(SoilTest.sample_date.desc()).limit(1))
    ).scalar_one_or_none()

    reminders = (
        (
            await db.execute(
                select(Reminder).where(Reminder.completed.is_(False)).order_by(Reminder.due_date.asc()).limit(5)
            )
        )
        .scalars()
        .all()
    )

    irrigation_by_zone = [
        {
            "zone_id": str(row.id),
            "zone_number": row.zone_number,
            "zone_name": row.name,
            "sqft": row.sqft,
            "inches": _num(row.inches) or 0,
            "zone_category": row.zone_category,
            "included_in_turf_budget": row.zone_category == "turf",
        }
        for row in irrigation_rows
    ]

    turf_rows = [row for row in irrigation_by_zone if row["included_in_turf_budget"]]
    turf_sqft_total = sum(int(row["sqft"] or 0) for row in turf_rows)
    if turf_rows and turf_sqft_total > 0:
        irrigation_turf_avg_7d = sum(row["inches"] * (int(row["sqft"] or 0) / turf_sqft_total) for row in turf_rows)
    elif turf_rows:
        irrigation_turf_avg_7d = sum(row["inches"] for row in turf_rows) / len(turf_rows)
    else:
        irrigation_turf_avg_7d = 0.0

    irrigation_all_zones_total_7d = sum(row["inches"] for row in irrigation_by_zone)
    irrigation_total_water_7d = irrigation_turf_avg_7d + (_num(rainfall_7d) or 0)
    irrigation_zone_events_count_7d = sum(1 for row in irrigation_by_zone if row["inches"] > 0)

    last_treatment = None
    if last_treatment_obj is not None:
        days_ago = max((now_utc - last_treatment_obj.applied_at).days, 0)
        first_tp = last_treatment_obj.products[0] if last_treatment_obj.products else None
        last_treatment = {
            "id": str(last_treatment_obj.id),
            "applied_at": last_treatment_obj.applied_at.isoformat(),
            "product_name": first_tp.product.name if first_tp else None,
            "days_ago": days_ago,
        }

    return {
        "weather": {
            "current": {
                "observed_at": latest_observation.observed_at.isoformat() if latest_observation else None,
                "temp_f": _num(latest_observation.temp_f) if latest_observation else None,
                "humidity_pct": _num(latest_observation.humidity_pct) if latest_observation else None,
                "wind_mph": _num(latest_observation.wind_mph) if latest_observation else None,
                "precip_in": _num(latest_observation.precip_in) if latest_observation else None,
            },
            "today_forecast": {
                "date": today_forecast.forecast_for_day.isoformat() if today_forecast else None,
                "temp_high_f": _num(today_forecast.temp_high_f) if today_forecast else None,
                "temp_low_f": _num(today_forecast.temp_low_f) if today_forecast else None,
                "precip_probability_pct": _num(today_forecast.precip_probability_pct) if today_forecast else None,
                "precip_amount_in": _num(today_forecast.precip_amount_in) if today_forecast else None,
                "conditions": today_forecast.conditions if today_forecast else None,
            },
            "next_7_days": next_7_days_forecast,
            "forecast_rainfall_7d_in": forecast_rainfall_7d_in,
            "rainfall_7d_in": _num(rainfall_7d) or 0,
        },
        "irrigation": {
            "total_water_7d_in": irrigation_total_water_7d,
            "turf_avg_7d_in": irrigation_turf_avg_7d,
            "all_zones_total_7d_in": irrigation_all_zones_total_7d,
            "zones_with_events_7d": irrigation_zone_events_count_7d,
            "excluded_zone_numbers": [
                row["zone_number"] for row in irrigation_by_zone if not row["included_in_turf_budget"]
            ],
            "calibration_note": (
                "Calibrate precipitation rate (in/hr) for each zone and verify soil type data "
                "before relying on irrigation depth decisions."
            ),
            "zones": irrigation_by_zone,
        },
        "last_treatment": last_treatment,
        "last_cultural_by_type": [
            {
                "id": str(practice.id),
                "practice_type": practice.practice_type,
                "performed_at": practice.performed_at.isoformat(),
                "days_ago": max((now_utc - practice.performed_at).days, 0),
            }
            for practice in latest_cultural_by_type.values()
        ],
        "last_soil_test": {
            "id": str(latest_soil_test.id),
            "sample_date": latest_soil_test.sample_date.isoformat(),
            "ph": _num(latest_soil_test.ph),
            "organic_matter_pct": _num(latest_soil_test.organic_matter_pct),
            "phosphorus_ppm": _num(latest_soil_test.phosphorus_ppm),
            "potassium_ppm": _num(latest_soil_test.potassium_ppm),
            "cec": _num(latest_soil_test.cec),
        }
        if latest_soil_test
        else None,
        "active_reminders": [
            {
                "id": str(reminder.id),
                "due_date": reminder.due_date.isoformat(),
                "reminder_type": reminder.reminder_type,
                "description": reminder.description,
            }
            for reminder in reminders
        ],
        "quick_actions": [
            {"label": "Log mow", "href": "/cultural"},
            {"label": "Log treatment", "href": "/treatments"},
            {"label": "Add product", "href": "/products/new"},
        ],
    }
