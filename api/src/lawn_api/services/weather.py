from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.integrations.openmeteo import OPENMETEO_SOURCE, fetch_openmeteo_weather
from lawn_api.models.entities import LawnProfile, WeatherForecast, WeatherObservation

DEFAULT_LATITUDE = 39.0473
DEFAULT_LONGITUDE = -95.6752

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
        "et0_in": _hourly_lookup(payload, observed_at, "et0_fao_evapotranspiration"),
        "gdd_base50": max(0.0, float(current.get("temperature_2m", 50.0)) - 50.0),
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
    now = datetime.now(UTC)
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

    await db.commit()

    observation_count = (
        await db.execute(
            select(func.count())
            .select_from(WeatherObservation)
            .where(WeatherObservation.source == OPENMETEO_SOURCE)
        )
    ).scalar_one()
    forecast_count = (
        await db.execute(
            select(func.count())
            .select_from(WeatherForecast)
            .where(WeatherForecast.source == OPENMETEO_SOURCE)
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
