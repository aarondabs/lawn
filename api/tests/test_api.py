from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from lawn_api.db import AsyncSessionLocal
from lawn_api.models.entities import WeatherForecast, WeatherObservation


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
            "product_type": "fertilizer_synthetic",
            "label_rate": 4.0,
            "label_rate_unit": "lb_per_1000",
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
            "performed_at": datetime.now(UTC).isoformat(),
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
async def test_mow_details_round_trip(client: AsyncClient) -> None:
    """Structured mow fields survive create and patch, and keep their types."""
    created = await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": datetime.now(UTC).isoformat(),
            "practice_type": "mow",
            "details": {"cut_height_inches": 3.75, "mow_orientation": "diagonal_ne_sw"},
        },
    )
    assert created.status_code == 201
    assert created.json()["details"] == {
        "cut_height_inches": 3.75,
        "mow_orientation": "diagonal_ne_sw",
    }
    practice_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/cultural-practices/{practice_id}",
        json={"details": {"cut_height_inches": 4.0, "mow_orientation": "east_west"}},
    )
    assert patched.status_code == 200
    assert patched.json()["details"]["mow_orientation"] == "east_west"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "details",
    [
        {"mow_orientation": "northsouth"},  # not in MOW_ORIENTATIONS
        {"cut_height_inches": 3.6},  # not a quarter-inch step
        {"cut_height_inches": 9.0},  # above MAX_CUT_HEIGHT_INCHES
        {"cut_height_inches": 0},  # must be positive
    ],
)
async def test_mow_details_rejects_bad_values(client: AsyncClient, details: dict) -> None:
    """details is JSONB with no CHECK constraint, so pydantic is the only guard."""
    response = await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": datetime.now(UTC).isoformat(),
            "practice_type": "mow",
            "details": details,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_mow_details_pass_through(client: AsyncClient) -> None:
    """Practices with no mow keys keep an arbitrary details blob untouched."""
    created = await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": datetime.now(UTC).isoformat(),
            "practice_type": "aerate",
            "details": {"tine_depth_inches": 3, "passes": 2},
        },
    )
    assert created.status_code == 201
    assert created.json()["details"] == {"tine_depth_inches": 3, "passes": 2}


@pytest.mark.asyncio
async def test_treatment_crud_flow(client: AsyncClient) -> None:
    herbicide = await client.post(
        "/api/v1/products",
        json={
            "name": "3-Way Mix",
            "manufacturer": "Acme",
            "product_type": "herbicide_post_broadleaf",
            "label_rate": 1.2,
            "label_rate_unit": "fl_oz_per_1000",
        },
    )
    assert herbicide.status_code == 201

    surfactant = await client.post(
        "/api/v1/products",
        json={
            "name": "Surfactant",
            "manufacturer": "Acme",
            "product_type": "surfactant",
            "label_rate": 1.5,
            "label_rate_unit": "fl_oz_per_gal",
        },
    )
    assert surfactant.status_code == 201

    equipment = await client.post(
        "/api/v1/equipment",
        json={"type": "sprayer", "make": "Echo", "model": "RB-60"},
    )
    assert equipment.status_code == 201

    created = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(UTC).isoformat(),
            "application_method": "granular",
            "products": [
                {
                    "product_id": herbicide.json()["id"],
                    "rate_applied": 1.2,
                    "rate_unit": "fl_oz_per_1000",
                },
                {
                    "product_id": surfactant.json()["id"],
                    "rate_applied": 1.5,
                    "rate_unit": "fl_oz_per_gal",
                },
            ],
            "area_treated_sqft": 5000,
            "equipment_id": equipment.json()["id"],
            "applicator": "self",
        },
    )
    assert created.status_code == 201
    treatment_id = created.json()["id"]
    assert len(created.json()["products"]) == 2

    listed = await client.get("/api/v1/treatments")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = await client.get(f"/api/v1/treatments/{treatment_id}")
    assert detail.status_code == 200
    assert len(detail.json()["products"]) == 2

    patched = await client.patch(
        f"/api/v1/treatments/{treatment_id}",
        json={
            "notes": "Applied before rain",
            "products": [
                {
                    "product_id": herbicide.json()["id"],
                    "rate_applied": 1.3,
                    "rate_unit": "fl_oz_per_1000",
                },
                {
                    "product_id": surfactant.json()["id"],
                    "rate_applied": 1.25,
                    "rate_unit": "fl_oz_per_gal",
                },
            ],
        },
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "Applied before rain"
    assert patched.json()["products"][0]["rate_applied"] == 1.3

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
        observation_count = (await db.execute(select(func.count()).select_from(WeatherObservation))).scalar_one()
        forecast_count = (await db.execute(select(func.count()).select_from(WeatherForecast))).scalar_one()

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
async def test_rachio_connect_upserts_zones(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
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

    async def fake_person_details(_: str, __: str) -> dict[str, Any]:
        return {"devices": [{"id": "device-1"}]}

    async def fake_events(*_: Any, **__: Any) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr("lawn_api.services.rachio.fetch_person_info", fake_person_info)
    monkeypatch.setattr("lawn_api.services.rachio.fetch_person_details", fake_person_details)
    monkeypatch.setattr("lawn_api.services.rachio.fetch_recent_events", fake_events)

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
                "eventDate": int((datetime.now(UTC) - timedelta(days=2)).timestamp() * 1000),
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


@pytest.mark.asyncio
async def test_reminder_crud_flow(client: AsyncClient) -> None:
    # Create
    created = await client.post(
        "/api/v1/reminders",
        json={"due_date": "2026-06-01", "reminder_type": "treatment", "description": "Apply pre-emergent"},
    )
    assert created.status_code == 201
    reminder_id = created.json()["id"]
    assert created.json()["completed"] is False

    # List (default: all)
    listed = await client.get("/api/v1/reminders")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # List filtered pending
    pending = await client.get("/api/v1/reminders?completed=false")
    assert len(pending.json()) == 1

    # Detail
    detail = await client.get(f"/api/v1/reminders/{reminder_id}")
    assert detail.status_code == 200
    assert detail.json()["description"] == "Apply pre-emergent"

    # Patch
    patched = await client.patch(
        f"/api/v1/reminders/{reminder_id}",
        json={"description": "Apply pre-emergent (updated)"},
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "Apply pre-emergent (updated)"

    # Snooze
    snoozed = await client.post(
        f"/api/v1/reminders/{reminder_id}/snooze",
        json={"new_due_date": "2026-06-15"},
    )
    assert snoozed.status_code == 200
    assert snoozed.json()["due_date"] == "2026-06-15"

    # Complete
    completed = await client.post(f"/api/v1/reminders/{reminder_id}/complete", json={})
    assert completed.status_code == 200
    assert completed.json()["completed"] is True
    assert completed.json()["completed_at"] is not None

    # Double-complete should 400
    double = await client.post(f"/api/v1/reminders/{reminder_id}/complete", json={})
    assert double.status_code == 400

    # Completed reminders show with ?completed=true
    done = await client.get("/api/v1/reminders?completed=true")
    assert len(done.json()) == 1

    # Delete
    deleted = await client.delete(f"/api/v1/reminders/{reminder_id}")
    assert deleted.status_code == 204

    # Gone
    gone = await client.get(f"/api/v1/reminders/{reminder_id}")
    assert gone.status_code == 404


# ---------------------------------------------------------------------------
# Phase 2a: liquid treatments, derived area, inventory
# ---------------------------------------------------------------------------


async def _liquid_fixtures(client: AsyncClient) -> tuple[str, str]:
    """A liquid product with tracked inventory, plus a sprayer."""
    product = await client.post(
        "/api/v1/products",
        json={
            "name": "3-Way Max",
            "manufacturer": "Acme",
            "product_type": "herbicide_post_broadleaf",
            "label_rate": 1.5,
            "label_rate_unit": "fl_oz_per_1000",
            "current_inventory": 1,
            "current_inventory_unit": "gal",
        },
    )
    assert product.status_code == 201, product.text

    sprayer = await client.post(
        "/api/v1/equipment",
        json={"type": "sprayer", "make": "Fimco", "model": "45 gal"},
    )
    assert sprayer.status_code == 201
    return product.json()["id"], sprayer.json()["id"]


def _fill(product_id: str, volume: float, amount: float) -> dict:
    return {
        "total_mix_volume": volume,
        "total_mix_volume_unit": "gal",
        "calibrated_rate_snapshot": 1.0,
        "calibrated_rate_unit_snapshot": "gal_per_1000",
        "products": [{"product_id": product_id, "amount_used": amount, "amount_used_unit": "fl_oz"}],
    }


@pytest.mark.asyncio
async def test_liquid_treatment_derives_area_from_fills(client: AsyncClient) -> None:
    """Area comes from mix volume / calibrated rate, summed across fills."""
    product_id, sprayer_id = await _liquid_fixtures(client)

    created = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(UTC).isoformat(),
            "application_method": "liquid",
            "equipment_id": sprayer_id,
            "applicator": "self",
            # 20 gal + 15 gal at 1 gal/1000 -> 20,000 + 15,000 sq ft
            "fills": [_fill(product_id, 20, 30), _fill(product_id, 15, 22)],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()

    assert body["area_treated_sqft"] == 35000
    assert [f["fill_number"] for f in body["fills"]] == [1, 2]
    assert float(body["fills"][0]["area_covered_sqft"]) == 20000
    assert float(body["fills"][1]["area_covered_sqft"]) == 15000

    # Effective rate is per 1,000 sq ft of the area that fill actually covered.
    assert float(body["fills"][0]["products"][0]["effective_rate_per_1000"]) == pytest.approx(1.5)


@pytest.mark.asyncio
async def test_liquid_treatment_rejects_supplied_area(client: AsyncClient) -> None:
    """Area is derived for liquid; supplying it is a mistake, not a hint."""
    product_id, sprayer_id = await _liquid_fixtures(client)
    response = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(UTC).isoformat(),
            "application_method": "liquid",
            "applicator": "self",
            "equipment_id": sprayer_id,
            "area_treated_sqft": 47000,
            "fills": [_fill(product_id, 20, 30)],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_granular_treatment_rejects_fills(client: AsyncClient) -> None:
    product_id, _ = await _liquid_fixtures(client)
    response = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(UTC).isoformat(),
            "application_method": "granular",
            "applicator": "self",
            "area_treated_sqft": 47000,
            "products": [{"product_id": product_id, "rate_applied": 1.5, "rate_unit": "fl_oz_per_1000"}],
            "fills": [_fill(product_id, 20, 30)],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_liquid_inventory_decrements_and_restores(client: AsyncClient) -> None:
    """The full lifecycle: apply consumes stock, delete puts it back."""
    product_id, sprayer_id = await _liquid_fixtures(client)

    # 1 gal = 128 fl oz on hand; 30 + 22 fl oz used -> 76 fl oz = 0.59375 gal left.
    created = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(UTC).isoformat(),
            "application_method": "liquid",
            "applicator": "self",
            "equipment_id": sprayer_id,
            "fills": [_fill(product_id, 20, 30), _fill(product_id, 15, 22)],
        },
    )
    assert created.status_code == 201, created.text
    treatment_id = created.json()["id"]

    after_apply = await client.get(f"/api/v1/products/{product_id}")
    assert float(after_apply.json()["current_inventory"]) == pytest.approx(0.59375)

    # Editing down to a single smaller fill restores the old amount first.
    patched = await client.patch(
        f"/api/v1/treatments/{treatment_id}",
        json={"fills": [_fill(product_id, 10, 16)]},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["area_treated_sqft"] == 10000

    after_edit = await client.get(f"/api/v1/products/{product_id}")
    assert float(after_edit.json()["current_inventory"]) == pytest.approx(0.875)  # 112/128

    deleted = await client.delete(f"/api/v1/treatments/{treatment_id}")
    assert deleted.status_code == 204

    after_delete = await client.get(f"/api/v1/products/{product_id}")
    assert float(after_delete.json()["current_inventory"]) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_inventory_warns_rather_than_guessing_density(client: AsyncClient) -> None:
    """A product stocked by weight but applied by volume must not be guessed at."""
    product = await client.post(
        "/api/v1/products",
        json={
            "name": "Ambiguous Product",
            "manufacturer": "Acme",
            "product_type": "fertilizer_synthetic",
            "label_rate": 1.0,
            "label_rate_unit": "fl_oz_per_1000",
            "current_inventory": 10,
            "current_inventory_unit": "lb",
        },
    )
    assert product.status_code == 201
    product_id = product.json()["id"]

    created = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(UTC).isoformat(),
            "application_method": "liquid",
            "applicator": "self",
            "fills": [_fill(product_id, 20, 30)],
        },
    )
    assert created.status_code == 201, created.text

    warnings = created.json()["inventory_warnings"]
    assert len(warnings) == 1
    assert "density" in warnings[0]["message"]

    # Stock is left untouched rather than silently corrupted.
    unchanged = await client.get(f"/api/v1/products/{product_id}")
    assert float(unchanged.json()["current_inventory"]) == 10.0


# ---------------------------------------------------------------------------
# Phase 2c Task 0.1: JSONB nulls must be SQL NULL, not the JSON scalar 'null'
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jsonb_absent_value_is_sql_null(client: AsyncClient) -> None:
    """Regression guard for the none_as_null defect.

    SQLAlchemy's JSONB renders Python None as JSON 'null' unless the column sets
    none_as_null=True, which makes `IS NULL` match nothing. A guardrail asking
    "which fertilizers lack a guaranteed analysis?" would then return an empty
    list and read as all-clear. This asserts the predicate actually works.
    """
    from sqlalchemy import func, select

    from lawn_api.db import AsyncSessionLocal
    from lawn_api.models.entities import Product

    with_analysis = await client.post(
        "/api/v1/products",
        json={
            "name": "Has Analysis",
            "manufacturer": "Acme",
            "product_type": "fertilizer_synthetic",
            "label_rate": 2.5,
            "label_rate_unit": "lb_per_1000",
            "guaranteed_analysis": {"total_nitrogen": "32.0%"},
        },
    )
    assert with_analysis.status_code == 201

    without = await client.post(
        "/api/v1/products",
        json={
            "name": "No Analysis",
            "manufacturer": "Acme",
            "product_type": "fertilizer_synthetic",
            "label_rate": 2.5,
            "label_rate_unit": "lb_per_1000",
        },
    )
    assert without.status_code == 201

    async with AsyncSessionLocal() as session:
        missing = (
            await session.execute(
                select(Product.name).where(Product.guaranteed_analysis.is_(None))
            )
        ).scalars().all()
        # The whole point: the product with no analysis must be found by IS NULL.
        assert missing == ["No Analysis"]

        # And it must not be stored as the JSON scalar 'null' either.
        json_nulls = (
            await session.execute(
                select(func.count()).select_from(Product).where(
                    func.jsonb_typeof(Product.guaranteed_analysis) == "null"
                )
            )
        ).scalar_one()
        assert json_nulls == 0
