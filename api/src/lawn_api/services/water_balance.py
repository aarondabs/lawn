"""Water balance: rainfall vs. irrigation over rolling windows.

Rainfall comes from weather_daily (inches on the ground everywhere). Irrigation
comes from irrigation_event.inches_applied, averaged across turf zones to a
single lawn-wide inches figure comparable to rainfall.

Drip zones (trees/shrubs) are excluded from the lawn total, as established --
watering a shrub bed is not lawn water. Their activity is reported separately so
it stays visible without polluting the lawn number.
"""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.models.entities import IrrigationEvent, IrrigationZone, WeatherDaily

WINDOWS = (7, 14, 30)
TURF = "turf"
DRIP = "trees_shrubs"


async def _rainfall_in(db: AsyncSession, since_date) -> float:
    total = (
        await db.execute(
            select(func.coalesce(func.sum(WeatherDaily.precip_sum_in), 0)).where(
                WeatherDaily.observation_date >= since_date
            )
        )
    ).scalar_one()
    return round(float(total), 2)


async def _turf_zone_inches(db: AsyncSession, since_dt: datetime) -> list[tuple[str, float]]:
    """Per turf zone, inches applied in the window (non-skipped events)."""
    rows = (
        await db.execute(
            select(
                IrrigationZone.name,
                func.coalesce(func.sum(IrrigationEvent.inches_applied), 0).label("inches"),
            )
            .outerjoin(
                IrrigationEvent,
                (IrrigationEvent.zone_id == IrrigationZone.id)
                & (IrrigationEvent.started_at >= since_dt)
                & (IrrigationEvent.skipped.is_(False)),
            )
            .where(IrrigationZone.zone_category == TURF, IrrigationZone.is_enabled.is_(True))
            .group_by(IrrigationZone.id, IrrigationZone.name)
        )
    ).all()
    return [(name, round(float(inches), 3)) for name, inches in rows]


async def compute_water_balance(db: AsyncSession, now: datetime) -> dict:
    windows: dict[str, dict] = {}
    for days in WINDOWS:
        since_dt = now - timedelta(days=days)
        since_date = since_dt.date()

        rainfall = await _rainfall_in(db, since_date)
        zone_inches = await _turf_zone_inches(db, since_dt)
        # Lawn-wide irrigation = mean across turf zones, comparable to rainfall
        # as a single inches-on-the-ground figure.
        lawn_irrigation = (
            round(sum(v for _, v in zone_inches) / len(zone_inches), 3) if zone_inches else 0.0
        )

        windows[str(days)] = {
            "rainfall_in": rainfall,
            "lawn_irrigation_in": lawn_irrigation,
            "total_in": round(rainfall + lawn_irrigation, 2),
            "zones": [{"name": name, "inches": inches} for name, inches in zone_inches],
        }

    # Drip activity in the last 7 days -- a visibility indicator, kept out of the
    # lawn total above.
    seven = now - timedelta(days=7)
    drip_events = (
        await db.execute(
            select(func.count())
            .select_from(IrrigationEvent)
            .join(IrrigationZone, IrrigationZone.id == IrrigationEvent.zone_id)
            .where(
                IrrigationZone.zone_category == DRIP,
                IrrigationEvent.started_at >= seven,
                IrrigationEvent.skipped.is_(False),
            )
        )
    ).scalar_one()

    return {
        "windows": windows,
        "drip_7d": {"event_count": int(drip_events)},
    }
