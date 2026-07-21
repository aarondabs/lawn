from typing import Any

import httpx

OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
# Historical daily data lives on a separate host from the forecast endpoint.
OPENMETEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPENMETEO_SOURCE = "openmeteo"


async def fetch_openmeteo_weather(latitude: float, longitude: float) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "UTC",
        "past_days": 7,
        "forecast_days": 10,
        "current": ("temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m,wind_gusts_10m,precipitation"),
        # Open-Meteo returns `time` implicitly; don't include it in the variable list.
        "hourly": "precipitation,soil_temperature_0cm,evapotranspiration",
        "daily": (
            "temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "precipitation_probability_max,wind_speed_10m_max,weather_code"
        ),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(OPENMETEO_FORECAST_URL, params=params)
        response.raise_for_status()
        return response.json()


async def fetch_openmeteo_archive(
    latitude: float, longitude: float, start_date: str, end_date: str
) -> dict[str, Any]:
    """Daily highs, lows and precipitation for a past date range.

    Used to backfill GDD from spring green-up; the forecast endpoint only
    reaches seven days back. Dates are ISO (YYYY-MM-DD).
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "UTC",
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(OPENMETEO_ARCHIVE_URL, params=params)
        response.raise_for_status()
        return response.json()
