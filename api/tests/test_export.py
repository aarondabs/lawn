"""CSV export tests."""

import csv
import io
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


async def _lawn(client: AsyncClient) -> None:
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


def _parse(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


@pytest.mark.asyncio
async def test_treatment_export_explodes_products_with_nitrogen(client: AsyncClient) -> None:
    """A granular fertilizer row carries its derived amount and nitrogen."""
    await _lawn(client)
    product = (await client.post("/api/v1/products", json={
        "name": "32-0-4", "manufacturer": "Acme", "product_type": "fertilizer_synthetic",
        "label_rate": 2.5, "label_rate_unit": "lb_per_1000",
        "guaranteed_analysis": {"total_nitrogen_pct": 32.0},
    })).json()
    await client.post("/api/v1/treatments", json={
        "applied_at": datetime.now(UTC).isoformat(),
        "application_method": "granular", "applicator": "self", "area_treated_sqft": 47000,
        "products": [{"product_id": product["id"], "rate_applied": 2.5, "rate_unit": "lb_per_1000"}],
    })

    r = await client.get("/api/v1/export/treatments.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    rows = _parse(r.text)
    assert len(rows) == 1
    row = rows[0]
    assert row["product"] == "32-0-4"
    # 2.5 lb/1000 * 47 = 117.5 lb used; * 32% = 37.6 lb N.
    assert float(row["amount_used"]) == pytest.approx(117.5, abs=0.1)
    assert float(row["nitrogen_lb"]) == pytest.approx(37.6, abs=0.1)


@pytest.mark.asyncio
async def test_products_export_includes_coverage(client: AsyncClient) -> None:
    await _lawn(client)
    await client.post("/api/v1/products", json={
        "name": "3-Way", "manufacturer": "Acme", "product_type": "herbicide_post_broadleaf",
        "label_rate": 1.5, "label_rate_unit": "fl_oz_per_1000",
        "current_inventory": 1, "current_inventory_unit": "gal",
    })
    r = await client.get("/api/v1/export/products.csv")
    rows = _parse(r.text)
    assert rows[0]["name"] == "3-Way"
    assert float(rows[0]["applications_remaining"]) == pytest.approx(1.8, abs=0.1)


@pytest.mark.asyncio
async def test_all_export_endpoints_ok_when_empty(client: AsyncClient) -> None:
    """Every export returns a valid header-only CSV when there's no data."""
    for path in [
        "treatments", "cultural-practices", "irrigation-events",
        "products", "soil-tests", "weather-daily",
    ]:
        r = await client.get(f"/api/v1/export/{path}.csv")
        assert r.status_code == 200, path
        assert r.text.splitlines()  # at least a header row
