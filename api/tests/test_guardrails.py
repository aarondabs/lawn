"""Guardrail evaluation tests.

These check both the math and the fail-loud contract: a guardrail that cannot
run because data is missing must say so, never pass silently.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from lawn_api.db import AsyncSessionLocal
from lawn_api.models.entities import TankFill, Treatment
from lawn_api.services.guardrails import evaluate_treatment


async def _product(client: AsyncClient, **overrides) -> dict:
    body = {
        "name": "Test Fert",
        "manufacturer": "Acme",
        "product_type": "fertilizer_synthetic",
        "label_rate": 2.5,
        "label_rate_unit": "lb_per_1000",
    }
    body.update(overrides)
    r = await client.post("/api/v1/products", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def _lawn(client: AsyncClient) -> None:
    # Guardrails normalise over the treatment's own area, but a profile is
    # required elsewhere; ensure one exists.
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


async def _granular_treatment(
    client: AsyncClient, product_id: str, rate: float, area: int, applied_at: datetime
) -> dict:
    r = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": applied_at.isoformat(),
            "application_method": "granular",
            "applicator": "self",
            "area_treated_sqft": area,
            "products": [{"product_id": product_id, "rate_applied": rate, "rate_unit": "lb_per_1000"}],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _evaluate(treatment_id: str) -> list:
    async with AsyncSessionLocal() as db:
        # Load relationships eagerly, exactly as the router does before calling
        # the service -- the guardrails walk treatment.products / .fills.
        treatment = (
            await db.execute(
                select(Treatment)
                .options(
                    selectinload(Treatment.products),
                    selectinload(Treatment.fills).selectinload(TankFill.products),
                )
                .where(Treatment.id == treatment_id)
            )
        ).scalar_one()
        return await evaluate_treatment(db, treatment)


@pytest.mark.asyncio
async def test_nitrogen_math_granular(client: AsyncClient) -> None:
    """A 32-0-4 at 2.5 lb/1,000 over the whole lawn is 0.8 lb N/1,000 -- under
    the 1.0 limit, so no caution."""
    await _lawn(client)
    product = await _product(
        client, name="32-0-4", guaranteed_analysis={"total_nitrogen_pct": 32.0}
    )
    treatment = await _granular_treatment(client, product["id"], 2.5, 47000, datetime.now(UTC))

    findings = await _evaluate(treatment["id"])
    n_findings = [f for f in findings if f.code.startswith("nitrogen_load")]
    # 2.5 lb/1000 * 32% = 0.8 lb N/1000, under 1.0 -> no caution, no missing data.
    assert n_findings == []


@pytest.mark.asyncio
async def test_nitrogen_over_30d_limit_cautions(client: AsyncClient) -> None:
    """A high-N application that pushes past 1.0 lb N/1,000 raises a caution."""
    await _lawn(client)
    product = await _product(
        client, name="High N", guaranteed_analysis={"total_nitrogen_pct": 46.0}
    )
    # 3.0 lb/1000 * 46% = 1.38 lb N/1000 > 1.0
    treatment = await _granular_treatment(client, product["id"], 3.0, 47000, datetime.now(UTC))

    findings = await _evaluate(treatment["id"])
    codes = {f.code for f in findings}
    assert "nitrogen_load_30d" in codes
    caution = next(f for f in findings if f.code == "nitrogen_load_30d")
    assert caution.severity == "caution"
    assert caution.numbers["this_application"] == pytest.approx(1.38, abs=0.01)


@pytest.mark.asyncio
async def test_nitrogen_missing_analysis_fails_loud(client: AsyncClient) -> None:
    """A fertilizer with no analysis must report cannot_evaluate, never pass."""
    await _lawn(client)
    product = await _product(client, name="Mystery Fert", guaranteed_analysis=None)
    treatment = await _granular_treatment(client, product["id"], 2.5, 47000, datetime.now(UTC))

    findings = await _evaluate(treatment["id"])
    missing = [f for f in findings if f.severity == "cannot_evaluate"]
    assert any(f.code == "nitrogen_load_data_missing" for f in missing)
    assert missing[0].product_name == "Mystery Fert"


@pytest.mark.asyncio
async def test_reapplication_interval_cautions(client: AsyncClient) -> None:
    await _lawn(client)
    product = await _product(
        client, name="Repeat", min_reapplication_days=30, guaranteed_analysis={"total_nitrogen_pct": 10.0}
    )
    now = datetime.now(UTC)
    await _granular_treatment(client, product["id"], 1.0, 47000, now - timedelta(days=10))
    recent = await _granular_treatment(client, product["id"], 1.0, 47000, now)

    findings = await _evaluate(recent["id"])
    reapp = [f for f in findings if f.code == "reapplication_interval"]
    assert len(reapp) == 1
    assert reapp[0].numbers["days_since_last"] == pytest.approx(10, abs=1)


@pytest.mark.asyncio
async def test_reapplication_missing_interval_fails_loud(client: AsyncClient) -> None:
    await _lawn(client)
    product = await _product(
        client, name="NoInterval", min_reapplication_days=None, guaranteed_analysis={"total_nitrogen_pct": 10.0}
    )
    now = datetime.now(UTC)
    await _granular_treatment(client, product["id"], 1.0, 47000, now - timedelta(days=5))
    recent = await _granular_treatment(client, product["id"], 1.0, 47000, now)

    findings = await _evaluate(recent["id"])
    assert any(f.code == "reapplication_data_missing" for f in findings)


@pytest.mark.asyncio
async def test_annual_maximum_cautions_on_second_application(client: AsyncClient) -> None:
    """GrubEx-style: annual max = one application's worth. A second trips it."""
    await _lawn(client)
    product = await _product(
        client,
        name="GrubEx-like",
        product_type="insecticide",
        label_rate=2.87,
        max_annual_rate=2.87,
        max_annual_rate_unit="lb_per_1000",
    )
    now = datetime.now(UTC)
    await _granular_treatment(client, product["id"], 2.87, 47000, now - timedelta(days=20))
    second = await _granular_treatment(client, product["id"], 2.87, 47000, now)

    findings = await _evaluate(second["id"])
    annual = [f for f in findings if f.code == "annual_maximum"]
    assert len(annual) == 1
    # Two applications at label rate -> ~5.74, over the 2.87 cap.
    assert annual[0].numbers["applied_season"] == pytest.approx(5.74, abs=0.02)


@pytest.mark.asyncio
async def test_annual_maximum_single_application_ok(client: AsyncClient) -> None:
    """One application at exactly the cap does not trip it."""
    await _lawn(client)
    product = await _product(
        client,
        name="GrubEx-once",
        product_type="insecticide",
        label_rate=2.87,
        max_annual_rate=2.87,
        max_annual_rate_unit="lb_per_1000",
    )
    only = await _granular_treatment(client, product["id"], 2.87, 47000, datetime.now(UTC))

    findings = await _evaluate(only["id"])
    assert not any(f.code == "annual_maximum" for f in findings)


@pytest.mark.asyncio
async def test_treatment_response_includes_findings(client: AsyncClient) -> None:
    """Findings surface on the save response, not only via the service."""
    await _lawn(client)
    product = await _product(
        client, name="Hot N", guaranteed_analysis={"total_nitrogen_pct": 46.0}
    )
    r = await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": datetime.now(UTC).isoformat(),
            "application_method": "granular",
            "applicator": "self",
            "area_treated_sqft": 47000,
            "products": [{"product_id": product["id"], "rate_applied": 3.0, "rate_unit": "lb_per_1000"}],
        },
    )
    assert r.status_code == 201
    codes = {f["code"] for f in r.json()["guardrail_findings"]}
    assert "nitrogen_load_30d" in codes


@pytest.mark.asyncio
async def test_overseed_after_preemergent_warns(client: AsyncClient) -> None:
    await _lawn(client)
    pre = await _product(
        client,
        name="Pre-M",
        product_type="herbicide_pre",
        label_rate=1.0,
        label_rate_unit="fl_oz_per_1000",
        preemergent_blocking_days=90,
    )
    now = datetime.now(UTC)
    # Pre-emergent applied 30 days ago; overseed today is well inside 90 days.
    await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": (now - timedelta(days=30)).isoformat(),
            "application_method": "granular",
            "applicator": "self",
            "area_treated_sqft": 47000,
            "products": [{"product_id": pre["id"], "rate_applied": 1.0, "rate_unit": "fl_oz_per_1000"}],
        },
    )
    r = await client.post(
        "/api/v1/cultural-practices",
        json={"performed_at": now.isoformat(), "practice_type": "overseed"},
    )
    assert r.status_code == 201
    codes = {f["code"] for f in r.json()["guardrail_findings"]}
    assert "preemergent_before_seed" in codes


@pytest.mark.asyncio
async def test_overseed_outside_window_no_warning(client: AsyncClient) -> None:
    await _lawn(client)
    pre = await _product(
        client,
        name="Pre-M2",
        product_type="herbicide_pre",
        label_rate=1.0,
        label_rate_unit="fl_oz_per_1000",
        preemergent_blocking_days=60,
    )
    now = datetime.now(UTC)
    await client.post(
        "/api/v1/treatments",
        json={
            "applied_at": (now - timedelta(days=90)).isoformat(),
            "application_method": "granular",
            "applicator": "self",
            "area_treated_sqft": 47000,
            "products": [{"product_id": pre["id"], "rate_applied": 1.0, "rate_unit": "fl_oz_per_1000"}],
        },
    )
    r = await client.post(
        "/api/v1/cultural-practices",
        json={"performed_at": now.isoformat(), "practice_type": "overseed"},
    )
    assert r.status_code == 201
    # 90 days out, window is 60 -> clear.
    assert r.json()["guardrail_findings"] == []


@pytest.mark.asyncio
async def test_current_state_endpoint(client: AsyncClient) -> None:
    """The dashboard endpoint returns outstanding cautions with no proposal."""
    await _lawn(client)
    product = await _product(
        client, name="Season N", guaranteed_analysis={"total_nitrogen_pct": 46.0}
    )
    # Two heavy applications push season-to-date over the 4.0 budget.
    now = datetime.now(UTC)
    for days in (40, 10):
        await client.post(
            "/api/v1/treatments",
            json={
                "applied_at": (now - timedelta(days=days)).isoformat(),
                "application_method": "granular",
                "applicator": "self",
                "area_treated_sqft": 47000,
                "products": [{"product_id": product["id"], "rate_applied": 5.0, "rate_unit": "lb_per_1000"}],
            },
        )
    r = await client.get("/api/v1/guardrails/current")
    assert r.status_code == 200
    codes = {f["code"] for f in r.json()}
    assert "nitrogen_load_season" in codes
