from typing import Any

import httpx

OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_SOURCE = "openmeteo"


async def fetch_openmeteo_weather(latitude: float, longitude: float) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "UTC",
        "forecast_days": 10,
        "current": (
            "temperature_2m,relative_humidity_2m,dew_point_2m,"
            "wind_speed_10m,wind_gusts_10m,precipitation"
        ),
        "hourly": "time,soil_temperature_0cm,et0_fao_evapotranspiration",
        "daily": (
            "time,temperature_2m_max,temperature_2m_min,precipitation_sum,"
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
