from datetime import date, datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from lawn_api.db import AsyncSessionLocal
from lawn_api.main import app
from lawn_api.models.entities import WeatherForecast, WeatherObservation


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE "
                "reminder, irrigation_event, weather_observation, weather_forecast, "
                "soil_test, treatment, cultural_practice, product, equipment, "
                "irrigation_zone, lawn_profile RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_lawn_profile_singleton_upsert_flow(client: AsyncClient) -> None:
    payload = {
        "total_sqft": 5000,
        "target_mow_height_inches": 3.5,
        "latitude": 39.0473,
        "longitude": -95.6752,
        "soil_type": "loam",
        "water_source": "city",
    }

    created = await client.post("/api/v1/lawn-profile", json=payload)
    assert created.status_code == 200
    first_id = created.json()["id"]

    updated = await client.post(
        "/api/v1/lawn-profile",
        json={**payload, "total_sqft": 5500},
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == first_id
    assert updated.json()["total_sqft"] == 5500

    patched = await client.patch("/api/v1/lawn-profile", json={"climate_notes": "Windy spring"})
    assert patched.status_code == 200
    assert patched.json()["climate_notes"] == "Windy spring"

    deleted = await client.delete("/api/v1/lawn-profile")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_irrigation_zone_crud_flow(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/irrigation-zones",
        json={
            "zone_number": 1,
            "name": "Front Lawn",
            "head_type": "rotor",
            "sun_exposure": "full_sun",
            "slope": "flat",
        },
    )
    assert created.status_code == 201
    zone_id = created.json()["id"]

    listed = await client.get("/api/v1/irrigation-zones")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/irrigation-zones/{zone_id}")
    assert detail.status_code == 200

    patched = await client.patch(
        f"/api/v1/irrigation-zones/{zone_id}",
        json={"notes": "Adjusted head angle"},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Adjusted head angle"

    deleted = await client.delete(f"/api/v1/irrigation-zones/{zone_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_equipment_crud_flow(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/equipment",
        json={"type": "sprayer", "make": "Ryobi", "model": "18V"},
    )
    assert created.status_code == 201
    equipment_id = created.json()["id"]

    listed = await client.get("/api/v1/equipment")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/equipment/{equipment_id}")
    assert detail.status_code == 200

    patched = await client.patch(
        f"/api/v1/equipment/{equipment_id}",
        json={"notes": "Calibrated"},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Calibrated"

    deleted = await client.delete(f"/api/v1/equipment/{equipment_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_product_crud_flow(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/products",
        json={
            "name": "Starter Fert",
            "manufacturer": "Acme",
            "product_type": "fertilizer",
            "label_rate": 4.0,
            "label_rate_unit": "lb",
        },
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    listed = await client.get("/api/v1/products")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/products/{product_id}")
    assert detail.status_code == 200

    patched = await client.patch(
        f"/api/v1/products/{product_id}",
        json={"notes": "Fall application"},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Fall application"

    deleted = await client.delete(f"/api/v1/products/{product_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_cultural_practice_crud_flow(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": datetime.now(timezone.utc).isoformat(),
            "practice_type": "mow",
        },
    )
    assert created.status_code == 201
    practice_id = created.json()["id"]

    listed = await client.get("/api/v1/cultural-practices")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/cultural-practices/{practice_id}")
    assert detail.status_code == 200

    patched = await client.patch(
        f"/api/v1/cultural-practices/{practice_id}",
        json={"notes": "Bagged clippings"},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Bagged clippings"

    deleted = await client.delete(f"/api/v1/cultural-practices/{practice_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_treatment_crud_flow(client: AsyncClient) -> None:
    product = await client.post(
        "/api/v1/products",
        json={
            "name": "Pre-Emergent",
            "manufacturer": "Acme",
            "product_type": "herbicide_pre",
            "label_rate": 2.0,
            "label_rate_unit": "lb",
        },
    )
    assert product.status_code == 201

    equipment = await client.post(
        "/api/v1/equipment",
        json={"type": "spreader", "make": "Echo", "model": "RB-60"},
    )
    assert equipment.status_code == 201

    created = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "product_id": product.json()["id"],
            "rate_applied": 2.5,
            "rate_unit": "lb",
            "area_treated_sqft": 5000,
            "equipment_id": equipment.json()["id"],
            "applicator": "self",
        },
    )
    assert created.status_code == 201
    treatment_id = created.json()["id"]

    listed = await client.get("/api/v1/treatments")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/treatments/{treatment_id}")
    assert detail.status_code == 200

    patched = await client.patch(
        f"/api/v1/treatments/{treatment_id}",
        json={"notes": "Applied before rain"},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Applied before rain"

    deleted = await client.delete(f"/api/v1/treatments/{treatment_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_soil_test_crud_flow(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/soil-tests",
        json={
            "sample_date": date.today().isoformat(),
            "lab_name": "MySoil",
            "ph": 6.4,
        },
    )
    assert created.status_code == 201
    soil_test_id = created.json()["id"]

    listed = await client.get("/api/v1/soil-tests")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/soil-tests/{soil_test_id}")
    assert detail.status_code == 200

    patched = await client.patch(
        f"/api/v1/soil-tests/{soil_test_id}",
        json={"notes": "Retest in spring"},
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Retest in spring"

    deleted = await client.delete(f"/api/v1/soil-tests/{soil_test_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_refresh_weather_endpoint_uses_profile_coords_and_persists(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await client.post(
        "/api/v1/lawn-profile",
        json={
            "total_sqft": 5000,
            "target_mow_height_inches": 3.5,
            "latitude": 40.11111,
            "longitude": -94.22222,
            "soil_type": "loam",
            "water_source": "city",
        },
    )

    called: dict[str, float] = {}

    async def fake_fetch_openmeteo_weather(latitude: float, longitude: float) -> dict[str, Any]:
        called["latitude"] = latitude
        called["longitude"] = longitude
        return {
            "current": {
                "time": "2026-05-06T12:00",
                "temperature_2m": 72.0,
                "relative_humidity_2m": 50,
                "dew_point_2m": 52.0,
                "wind_speed_10m": 8.0,
                "wind_gusts_10m": 12.0,
                "precipitation": 0.0,
            },
            "hourly": {
                "time": ["2026-05-06T12:00"],
                "soil_temperature_0cm": [66.0],
                "et0_fao_evapotranspiration": [0.1],
            },
            "daily": {
                "time": [
                    "2026-05-06",
                    "2026-05-07",
                ],
                "temperature_2m_max": [78.0, 80.0],
                "temperature_2m_min": [60.0, 61.0],
                "precipitation_probability_max": [10, 20],
                "precipitation_sum": [0.0, 0.1],
                "wind_speed_10m_max": [12.0, 13.0],
                "weather_code": [1, 3],
            },
        }

    monkeypatch.setattr(
        "lawn_api.services.weather.fetch_openmeteo_weather",
        fake_fetch_openmeteo_weather,
    )

    response = await client.post("/api/v1/admin/refresh-weather")
    assert response.status_code == 200
    assert called["latitude"] == 40.11111
    assert called["longitude"] == -94.22222
    assert response.json()["forecast_rows_stored"] == 2

    async with AsyncSessionLocal() as db:
        observation_count = (
            await db.execute(select(func.count()).select_from(WeatherObservation))
        ).scalar_one()
        forecast_count = (
            await db.execute(select(func.count()).select_from(WeatherForecast))
        ).scalar_one()

    assert observation_count == 1
    assert forecast_count == 2


@pytest.mark.asyncio
async def test_refresh_weather_endpoint_falls_back_to_topeka_coords(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, float] = {}

    async def fake_fetch_openmeteo_weather(latitude: float, longitude: float) -> dict[str, Any]:
        seen["latitude"] = latitude
        seen["longitude"] = longitude
        return {
            "current": {
                "time": "2026-05-06T12:00",
                "temperature_2m": 70.0,
                "relative_humidity_2m": 40,
                "dew_point_2m": 45.0,
                "wind_speed_10m": 7.0,
                "wind_gusts_10m": 11.0,
                "precipitation": 0.0,
            },
            "hourly": {
                "time": ["2026-05-06T12:00"],
                "soil_temperature_0cm": [64.0],
                "et0_fao_evapotranspiration": [0.09],
            },
            "daily": {
                "time": ["2026-05-06"],
                "temperature_2m_max": [75.0],
                "temperature_2m_min": [58.0],
                "precipitation_probability_max": [5],
                "precipitation_sum": [0.0],
                "wind_speed_10m_max": [10.0],
                "weather_code": [0],
            },
        }

    monkeypatch.setattr(
        "lawn_api.services.weather.fetch_openmeteo_weather",
        fake_fetch_openmeteo_weather,
    )

    response = await client.post("/api/v1/admin/refresh-weather")
    assert response.status_code == 200
    assert seen["latitude"] == 39.0473
    assert seen["longitude"] == -95.6752


@pytest.mark.asyncio
async def test_rachio_connect_upserts_zones(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("lawn_api.services.rachio.settings.rachio_api_key", "test-key")

    async def fake_person_info(_: str) -> dict[str, Any]:
        return {
            "id": "person-1",
            "devices": [
                {
                    "zones": [
                        {
                            "id": "zone-ext-1",
                            "zoneNumber": 1,
                            "name": "Front",
                            "areaSqFt": 2500,
                            "zoneType": "rotor",
                            "nozzleInchesPerHour": 0.6,
                            "gpm": 2.1,
                            "sunlightExposure": "full sun",
                            "slope": "flat",
                            "soilType": "loam",
                        }
                    ]
                }
            ],
        }

    monkeypatch.setattr("lawn_api.services.rachio.fetch_person_info", fake_person_info)

    connected = await client.post("/api/v1/rachio/connect")
    assert connected.status_code == 200
    assert connected.json()["zones_created"] == 1

    zones = await client.get("/api/v1/irrigation-zones")
    assert zones.status_code == 200
    assert len(zones.json()) == 1
    assert zones.json()[0]["rachio_zone_id"] == "zone-ext-1"


@pytest.mark.asyncio
async def test_rachio_poll_inserts_events(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lawn_api.services.rachio.settings.rachio_api_key", "test-key")

    await client.post(
        "/api/v1/irrigation-zones",
        json={
            "zone_number": 1,
            "name": "Front Lawn",
            "head_type": "rotor",
            "sun_exposure": "full_sun",
            "slope": "flat",
            "rachio_zone_id": "zone-ext-1",
            "precipitation_rate_in_per_hr": 0.55,
        },
    )

    async def fake_person_info(_: str) -> dict[str, Any]:
        return {"id": "person-1", "devices": []}

    async def fake_person_details(_: str, __: str) -> dict[str, Any]:
        return {"devices": [{"id": "device-1"}]}

    async def fake_events(*_: Any, **__: Any) -> list[dict[str, Any]]:
        return [
            {
                "id": "event-1",
                "zoneId": "zone-ext-1",
                "eventDate": "2026-05-06T10:00:00+00:00",
                "duration": 1200,
                "source": "rachio",
                "skipped": False,
            }
        ]

    monkeypatch.setattr("lawn_api.services.rachio.fetch_person_info", fake_person_info)
    monkeypatch.setattr("lawn_api.services.rachio.fetch_person_details", fake_person_details)
    monkeypatch.setattr("lawn_api.services.rachio.fetch_recent_events", fake_events)

    polled = await client.post("/api/v1/admin/poll-rachio?lookback_hours=168")
    assert polled.status_code == 200
    assert polled.json()["events_inserted"] == 1


@pytest.mark.asyncio
async def test_rachio_poll_parses_summary_zone_events(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("lawn_api.services.rachio.settings.rachio_api_key", "test-key")

    await client.post(
        "/api/v1/irrigation-zones",
        json={
            "zone_number": 13,
            "name": "Back Corner",
            "head_type": "rotor",
            "sun_exposure": "full_sun",
            "slope": "flat",
            "rachio_zone_id": "zone-ext-13",
            "precipitation_rate_in_per_hr": 0.6,
        },
    )

    async def fake_person_info(_: str) -> dict[str, Any]:
        return {"id": "person-1", "devices": []}

    async def fake_person_details(_: str, __: str) -> dict[str, Any]:
        return {"devices": [{"id": "device-1"}]}

    async def fake_events(*_: Any, **__: Any) -> list[dict[str, Any]]:
        return [
            {
                "id": "event-zone-completed-1",
                "type": "ZONE_STATUS",
                "subType": "ZONE_COMPLETED",
                "summary": "Zone 13 completed watering at 10:11 AM (CDT) for 16 minutes.",
                "eventDate": 1777821076000,
            }
        ]

    monkeypatch.setattr("lawn_api.services.rachio.fetch_person_info", fake_person_info)
    monkeypatch.setattr("lawn_api.services.rachio.fetch_person_details", fake_person_details)
    monkeypatch.setattr("lawn_api.services.rachio.fetch_recent_events", fake_events)

    polled = await client.post("/api/v1/admin/poll-rachio?lookback_hours=168")
    assert polled.status_code == 200
    assert polled.json()["events_inserted"] == 1

    summary = await client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["irrigation"]["zones"]
    assert payload["irrigation"]["zones"][0]["zone_name"] == "Back Corner"
    assert payload["irrigation"]["zones"][0]["inches"] > 0


@pytest.mark.asyncio
async def test_rachio_webhook_accepts_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/webhooks/rachio",
        json={"event": "ZONE_COMPLETED", "zoneId": "zone-ext-1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
