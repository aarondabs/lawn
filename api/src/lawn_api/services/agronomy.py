"""Derived agronomic metrics for the dashboard.

Read-only computations over recorded history: growing-degree-day accumulation,
days-since markers, and the soil-temperature trend. Each degrades gracefully
when its data is thin -- early-season GDD, no mow logged yet -- returning nulls
the UI can render as "--" rather than raising.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.models.entities import (
    CulturalPractice,
    FillProduct,
    Product,
    TankFill,
    Treatment,
    TreatmentProduct,
    WeatherDaily,
    WeatherObservation,
)
from lawn_api.services import settings as app_settings

CENTRAL = ZoneInfo("America/Chicago")


def _green_up_start(today: date, month_day: str) -> date:
    """Most recent green-up date on/before today."""
    try:
        month, day = (int(p) for p in month_day.split("-"))
        candidate = date(today.year, month, day)
    except (ValueError, TypeError):
        candidate = date(today.year, 3, 15)
    if candidate > today:
        return date(candidate.year - 1, candidate.month, candidate.day)
    return candidate


async def gdd_accumulation(db: AsyncSession, now: datetime) -> dict:
    """Season-to-date GDD (base 50) since green-up, plus the latest day's value."""
    today = now.astimezone(CENTRAL).date()
    month_day = await app_settings.get_str(db, app_settings.GDD_GREEN_UP_MONTH_DAY, "03-15")
    green_up = _green_up_start(today, month_day)

    total, days_counted = (
        await db.execute(
            select(func.coalesce(func.sum(WeatherDaily.gdd_base50), 0), func.count(WeatherDaily.gdd_base50)).where(
                WeatherDaily.observation_date >= green_up,
                WeatherDaily.gdd_base50.isnot(None),
            )
        )
    ).one()

    latest = (
        await db.execute(
            select(WeatherDaily.gdd_base50)
            .where(WeatherDaily.gdd_base50.isnot(None))
            .order_by(WeatherDaily.observation_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return {
        "since_green_up": float(total),
        "green_up_date": green_up.isoformat(),
        "days_counted": int(days_counted),
        "latest_day": float(latest) if latest is not None else None,
    }


def _days_since(latest_dt: datetime | None, now: datetime) -> int | None:
    return None if latest_dt is None else (now - latest_dt).days


async def _last_treatment_with_type_prefix(db: AsyncSession, prefix: str) -> datetime | None:
    """Most recent treatment including a product whose type starts with `prefix`.

    Checks both paths -- granular via treatment_product and liquid via
    tank_fill/fill_product -- since a product of a type can arrive either way.
    """
    granular = (
        select(TreatmentProduct.treatment_id)
        .join(Product, Product.id == TreatmentProduct.product_id)
        .where(Product.product_type.like(f"{prefix}%"))
    )
    liquid = (
        select(TankFill.treatment_id)
        .join(FillProduct, FillProduct.tank_fill_id == TankFill.id)
        .join(Product, Product.id == FillProduct.product_id)
        .where(Product.product_type.like(f"{prefix}%"))
    )
    return (
        await db.execute(
            select(func.max(Treatment.applied_at)).where(
                Treatment.id.in_(granular.union(liquid))
            )
        )
    ).scalar_one_or_none()


async def days_since_markers(db: AsyncSession, now: datetime) -> dict:
    """Days since the last mow, last treatment, and last fertilizer/herbicide."""
    last_mow = (
        await db.execute(
            select(func.max(CulturalPractice.performed_at)).where(CulturalPractice.practice_type == "mow")
        )
    ).scalar_one_or_none()
    last_treatment = (await db.execute(select(func.max(Treatment.applied_at)))).scalar_one_or_none()
    last_fertilizer = await _last_treatment_with_type_prefix(db, "fertilizer")
    last_herbicide = await _last_treatment_with_type_prefix(db, "herbicide")

    return {
        "mow": _days_since(last_mow, now),
        "treatment": _days_since(last_treatment, now),
        "fertilizer": _days_since(last_fertilizer, now),
        "herbicide": _days_since(last_herbicide, now),
        "last_mow_at": last_mow.isoformat() if last_mow else None,
        "last_treatment_at": last_treatment.isoformat() if last_treatment else None,
    }


async def soil_temperature_trend(db: AsyncSession, now: datetime) -> dict:
    """Latest soil temp, 7-day average, and direction vs the prior 7 days."""
    seven = now - timedelta(days=7)
    fourteen = now - timedelta(days=14)

    latest = (
        await db.execute(
            select(WeatherObservation.soil_temp_f)
            .where(WeatherObservation.soil_temp_f.isnot(None))
            .order_by(WeatherObservation.observed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    avg_recent = (
        await db.execute(
            select(func.avg(WeatherObservation.soil_temp_f)).where(
                WeatherObservation.observed_at >= seven, WeatherObservation.soil_temp_f.isnot(None)
            )
        )
    ).scalar_one_or_none()

    avg_prior = (
        await db.execute(
            select(func.avg(WeatherObservation.soil_temp_f)).where(
                WeatherObservation.observed_at >= fourteen,
                WeatherObservation.observed_at < seven,
                WeatherObservation.soil_temp_f.isnot(None),
            )
        )
    ).scalar_one_or_none()

    trend = None
    if avg_recent is not None and avg_prior is not None:
        delta = float(avg_recent) - float(avg_prior)
        trend = "rising" if delta > 0.5 else "falling" if delta < -0.5 else "steady"

    return {
        "latest_f": float(latest) if latest is not None else None,
        "avg_7d_f": round(float(avg_recent), 1) if avg_recent is not None else None,
        "trend": trend,
    }
