from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.integrations.openmeteo import (
    OPENMETEO_SOURCE,
    fetch_openmeteo_archive,
    fetch_openmeteo_weather,
)
from lawn_api.models.entities import (
    LawnProfile,
    WeatherDaily,
    WeatherForecast,
    WeatherObservation,
)

DEFAULT_LATITUDE = 39.0473
DEFAULT_LONGITUDE = -95.6752

GDD_BASE_F = 50.0


def _compute_gdd(high: float | None, low: float | None) -> float | None:
    """Daily growing-degree-days, base 50F. NULL when a temperature is missing.

    NULL rather than 0 so a day with no reading is skipped by the accumulation
    SUM instead of dragging the total down as if it were a cold day.
    """
    if high is None or low is None:
        return None
    return max(0.0, (float(high) + float(low)) / 2.0 - GDD_BASE_F)


def _daily_rows_from_block(daily: dict[str, Any]) -> list[dict[str, Any]]:
    """Build weather_daily upsert rows from an Open-Meteo daily block."""
    days = daily.get("time", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])

    rows: list[dict[str, Any]] = []
    for idx, day in enumerate(days):
        high = highs[idx] if idx < len(highs) else None
        low = lows[idx] if idx < len(lows) else None
        rows.append(
            {
                "observation_date": day,
                "source": OPENMETEO_SOURCE,
                "temp_high_f": high,
                "temp_low_f": low,
                "gdd_base50": _compute_gdd(high, low),
                "precip_sum_in": precip[idx] if idx < len(precip) else None,
            }
        )
    return rows


async def _upsert_weather_daily(db: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Upsert daily rows, refreshing values so a provisional day is corrected."""
    if not rows:
        return 0
    stmt = insert(WeatherDaily).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["observation_date", "source"],
        set_={
            "temp_high_f": stmt.excluded.temp_high_f,
            "temp_low_f": stmt.excluded.temp_low_f,
            "gdd_base50": stmt.excluded.gdd_base50,
            "precip_sum_in": stmt.excluded.precip_sum_in,
        },
    )
    await db.execute(stmt)
    return len(rows)

WEATHER_CODE_TO_CONDITIONS = {
    0: "clear_sky",
    1: "mainly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing_rime_fog",
    51: "drizzle_light",
    53: "drizzle_moderate",
    55: "drizzle_dense",
    61: "rain_slight",
    63: "rain_moderate",
    65: "rain_heavy",
    71: "snow_slight",
    73: "snow_moderate",
    75: "snow_heavy",
    80: "rain_showers_slight",
    81: "rain_showers_moderate",
    82: "rain_showers_violent",
    95: "thunderstorm",
}


def _hourly_lookup(payload: dict[str, Any], timestamp: datetime, key: str) -> float | None:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    values = hourly.get(key, [])
    if not times or not values:
        return None

    # Open-Meteo returns RFC3339-ish UTC timestamps (without Z in some cases).
    target = timestamp.replace(minute=0, second=0, microsecond=0)
    for idx, raw_time in enumerate(times):
        hourly_time = datetime.fromisoformat(raw_time).replace(tzinfo=UTC)
        if hourly_time == target:
            return values[idx]
    return None


async def _get_coordinates(db: AsyncSession) -> tuple[float, float]:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    if profile is None:
        return DEFAULT_LATITUDE, DEFAULT_LONGITUDE
    return float(profile.latitude), float(profile.longitude)


def _to_utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


async def refresh_weather(db: AsyncSession) -> dict[str, Any]:
    latitude, longitude = await _get_coordinates(db)
    payload = await fetch_openmeteo_weather(latitude, longitude)

    now = datetime.now(UTC)

    hourly = payload.get("hourly", {})
    hourly_times = hourly.get("time", [])
    hourly_precip = hourly.get("precipitation", [])
    hourly_soil_temp = hourly.get("soil_temperature_0cm", [])
    hourly_et = hourly.get("evapotranspiration", [])

    hourly_rows: list[dict[str, Any]] = []
    for idx, raw_time in enumerate(hourly_times):
        observed_at = _to_utc(raw_time)
        if observed_at > now:
            continue
        hourly_rows.append(
            {
                "observed_at": observed_at,
                "source": OPENMETEO_SOURCE,
                "temp_f": None,
                "humidity_pct": None,
                "dew_point_f": None,
                "wind_mph": None,
                "wind_gust_mph": None,
                "precip_in": hourly_precip[idx] if idx < len(hourly_precip) else None,
                "soil_temp_f": hourly_soil_temp[idx] if idx < len(hourly_soil_temp) else None,
                "et0_in": hourly_et[idx] if idx < len(hourly_et) else None,
            }
        )

    if hourly_rows:
        hourly_stmt = insert(WeatherObservation).values(hourly_rows)
        hourly_stmt = hourly_stmt.on_conflict_do_update(
            index_elements=["observed_at", "source"],
            set_={
                "precip_in": hourly_stmt.excluded.precip_in,
                "soil_temp_f": hourly_stmt.excluded.soil_temp_f,
                "et0_in": hourly_stmt.excluded.et0_in,
            },
        )
        await db.execute(hourly_stmt)

    current = payload.get("current", {})
    observed_at = _to_utc(current["time"])

    observation_values = {
        "observed_at": observed_at,
        "source": OPENMETEO_SOURCE,
        "temp_f": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "dew_point_f": current.get("dew_point_2m"),
        "wind_mph": current.get("wind_speed_10m"),
        "wind_gust_mph": current.get("wind_gusts_10m"),
        "precip_in": current.get("precipitation"),
        "soil_temp_f": _hourly_lookup(payload, observed_at, "soil_temperature_0cm"),
        "et0_in": _hourly_lookup(payload, observed_at, "evapotranspiration"),
    }

    observation_stmt = insert(WeatherObservation).values(**observation_values)
    observation_stmt = observation_stmt.on_conflict_do_update(
        index_elements=["observed_at", "source"],
        set_={k: v for k, v in observation_values.items() if k not in {"observed_at", "source"}},
    )
    await db.execute(observation_stmt)

    await db.execute(delete(WeatherForecast).where(WeatherForecast.source == OPENMETEO_SOURCE))

    daily = payload.get("daily", {})
    days = daily.get("time", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    precip_prob = daily.get("precipitation_probability_max", [])
    precip_amount = daily.get("precipitation_sum", [])
    wind = daily.get("wind_speed_10m_max", [])
    weather_codes = daily.get("weather_code", [])

    forecast_rows = []
    for idx, day in enumerate(days):
        forecast_for = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=UTC)
        weather_code = weather_codes[idx] if idx < len(weather_codes) else None
        conditions = WEATHER_CODE_TO_CONDITIONS.get(weather_code, str(weather_code))

        forecast_rows.append(
            {
                "forecast_for": forecast_for,
                "fetched_at": now,
                "source": OPENMETEO_SOURCE,
                "temp_high_f": highs[idx] if idx < len(highs) else None,
                "temp_low_f": lows[idx] if idx < len(lows) else None,
                "precip_probability_pct": precip_prob[idx] if idx < len(precip_prob) else None,
                "precip_amount_in": precip_amount[idx] if idx < len(precip_amount) else None,
                "wind_mph": wind[idx] if idx < len(wind) else None,
                "conditions": conditions,
            }
        )

    if forecast_rows:
        await db.execute(insert(WeatherForecast), forecast_rows)

    # Persist the daily block into weather_daily too. The forecast fetch carries
    # past_days:7, so this keeps the recent tail current; the archive backfill
    # fills the deeper season history.
    await _upsert_weather_daily(db, _daily_rows_from_block(daily))

    await db.commit()

    observation_count = (
        await db.execute(
            select(func.count()).select_from(WeatherObservation).where(WeatherObservation.source == OPENMETEO_SOURCE)
        )
    ).scalar_one()
    forecast_count = (
        await db.execute(
            select(func.count()).select_from(WeatherForecast).where(WeatherForecast.source == OPENMETEO_SOURCE)
        )
    ).scalar_one()

    return {
        "status": "ok",
        "source": OPENMETEO_SOURCE,
        "latitude": latitude,
        "longitude": longitude,
        "observations_stored": int(observation_count),
        "forecast_rows_stored": int(forecast_count),
    }


async def backfill_weather_daily(db: AsyncSession, start_date: str, end_date: str) -> dict[str, Any]:
    """Populate weather_daily for a past date range from the archive API.

    One-time (or occasional) operation to give GDD a full season of history.
    Idempotent: re-running over the same range refreshes rather than duplicates.
    """
    latitude, longitude = await _get_coordinates(db)
    payload = await fetch_openmeteo_archive(latitude, longitude, start_date, end_date)
    rows = _daily_rows_from_block(payload.get("daily", {}))
    stored = await _upsert_weather_daily(db, rows)
    await db.commit()
    return {
        "status": "ok",
        "start_date": start_date,
        "end_date": end_date,
        "days_stored": stored,
    }
