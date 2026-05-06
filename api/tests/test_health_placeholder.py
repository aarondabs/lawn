from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from lawn_api.db import AsyncSessionLocal
from lawn_api.main import app


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
