"""Agronomy metric tests -- GDD accumulation, days-since, soil-temp trend."""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient

from lawn_api.db import AsyncSessionLocal
from lawn_api.models.entities import WeatherDaily, WeatherObservation
from lawn_api.services.agronomy import gdd_accumulation
from lawn_api.services.weather import _compute_gdd


def test_compute_gdd_math() -> None:
    # (80 + 60)/2 - 50 = 20
    assert _compute_gdd(80, 60) == 20.0
    # Below base -> clamped to 0, never negative.
    assert _compute_gdd(48, 40) == 0.0
    # Missing a temperature -> None, so the day is skipped, not counted as 0.
    assert _compute_gdd(80, None) is None
    assert _compute_gdd(None, None) is None


@pytest.mark.asyncio
async def test_gdd_accumulation_sums_since_green_up(client: AsyncClient) -> None:
    """GDD sums whole days since green-up and skips days with no reading."""
    today = datetime.now(UTC).date()
    async with AsyncSessionLocal() as db:
        # Three days this month: two valid, one missing temps (should be skipped).
        db.add_all(
            [
                WeatherDaily(
                    observation_date=today - timedelta(days=2),
                    source="openmeteo",
                    temp_high_f=80,
                    temp_low_f=60,
                    gdd_base50=20,
                ),
                WeatherDaily(
                    observation_date=today - timedelta(days=1),
                    source="openmeteo",
                    temp_high_f=90,
                    temp_low_f=70,
                    gdd_base50=30,
                ),
                WeatherDaily(
                    observation_date=today,
                    source="openmeteo",
                    temp_high_f=None,
                    temp_low_f=None,
                    gdd_base50=None,
                ),
                # A day before this year's green-up must not count.
                WeatherDaily(
                    observation_date=date(today.year - 1, 12, 1),
                    source="openmeteo",
                    temp_high_f=100,
                    temp_low_f=80,
                    gdd_base50=40,
                ),
            ]
        )
        await db.commit()

        result = await gdd_accumulation(db, datetime.now(UTC))

    # 20 + 30, the pre-green-up 40 and the null day excluded.
    assert result["since_green_up"] == 50.0
    assert result["days_counted"] == 2


@pytest.mark.asyncio
async def test_widgets_endpoint_shape(client: AsyncClient) -> None:
    r = await client.get("/api/v1/dashboard/widgets")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "gdd",
        "days_since",
        "soil_temp",
        "outstanding_cautions",
        "irrigation_skips_7d",
    }
    # Thin data degrades to nulls, not errors.
    assert body["days_since"]["mow"] is None
    assert body["gdd"]["since_green_up"] == 0.0


@pytest.mark.asyncio
async def test_days_since_mow(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": (datetime.now(UTC) - timedelta(days=3)).isoformat(),
            "practice_type": "mow",
        },
    )
    r = await client.get("/api/v1/dashboard/widgets")
    assert r.json()["days_since"]["mow"] == 3


@pytest.mark.asyncio
async def test_soil_temp_trend(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        # Prior week ~60F, recent week ~70F -> rising.
        for days, temp in [(10, 60), (9, 61), (3, 70), (1, 71)]:
            db.add(
                WeatherObservation(
                    observed_at=now - timedelta(days=days), source="openmeteo", soil_temp_f=temp
                )
            )
        await db.commit()

    r = await client.get("/api/v1/dashboard/widgets")
    soil = r.json()["soil_temp"]
    assert soil["trend"] == "rising"
    assert soil["latest_f"] == 71.0


# ---------------------------------------------------------------------------
# Coverage remaining (replaces the Task 4.2 static threshold)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_applications_remaining_computed(client: AsyncClient) -> None:
    """1 gal of a 1.5 fl_oz/1,000 product over 47,000 sqft = ~1.8 applications."""
    await client.post(
        "/api/v1/lawn-profile",
        json={
            "total_sqft": 47000,
            "target_mow_height_inches": 4.0,
            "latitude": 39.05,
            "longitude": -95.68,
            "soil_type": "silty_clay_loam",
            "water_source": "city",
        },
    )
    r = await client.post(
        "/api/v1/products",
        json={
            "name": "3-Way",
            "manufacturer": "Acme",
            "product_type": "herbicide_post_broadleaf",
            "label_rate": 1.5,
            "label_rate_unit": "fl_oz_per_1000",
            "current_inventory": 1,
            "current_inventory_unit": "gal",
        },
    )
    assert r.status_code == 201
    # 1 gal = 128 fl oz; one app = 1.5 * 47 = 70.5 fl oz; 128/70.5 = 1.815
    assert r.json()["applications_remaining"] == pytest.approx(1.815, abs=0.01)


@pytest.mark.asyncio
async def test_applications_remaining_none_for_surfactant(client: AsyncClient) -> None:
    """A pct_vv surfactant has no per-lawn coverage -- returns null, not a guess."""
    await client.post(
        "/api/v1/lawn-profile",
        json={
            "total_sqft": 47000,
            "target_mow_height_inches": 4.0,
            "latitude": 39.05,
            "longitude": -95.68,
            "soil_type": "silty_clay_loam",
            "water_source": "city",
        },
    )
    r = await client.post(
        "/api/v1/products",
        json={
            "name": "Surfactant",
            "manufacturer": "Acme",
            "product_type": "surfactant",
            "label_rate": 0.25,
            "label_rate_unit": "pct_vv",
            "current_inventory": 0.5,
            "current_inventory_unit": "gal",
        },
    )
    assert r.json()["applications_remaining"] is None
