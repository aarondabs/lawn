"""Context bundle assembly + LLM provider configuration tests.

No test here calls the real Anthropic API. The end-to-end check is the
deliberate, billable `lawn_api.scripts.assistant_smoke` run.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from lawn_api.config import settings as app_config
from lawn_api.integrations.llm import LLMError, get_llm_provider
from lawn_api.prompts import load_system_prompt


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


async def _build_bundle():
    from lawn_api.db import AsyncSessionLocal
    from lawn_api.services.context_bundle import build_context_bundle

    async with AsyncSessionLocal() as db:
        return await build_context_bundle(db, datetime.now(UTC))


@pytest.mark.asyncio
async def test_bundle_has_every_section_and_a_clean_split(client: AsyncClient) -> None:
    await _lawn(client)
    bundle = await _build_bundle()

    for tag in [
        "lawn_profile", "equipment", "products", "soil_tests", "irrigation_zones",
        "treatments", "cultural_practices", "app_settings", "current_datetime",
        "weather_daily_last_30d", "gdd", "soil_temperature", "forecast",
        "water_balance", "recent_irrigation", "guardrail_findings", "open_reminders",
    ]:
        assert f"<{tag}>" in bundle.full, f"missing section {tag}"

    # Stable/volatile placement: history before the cache breakpoint, live state after.
    assert "<products>" in bundle.stable and "<products>" not in bundle.volatile
    assert "<guardrail_findings>" in bundle.volatile and "<guardrail_findings>" not in bundle.stable
    assert bundle.full == f"{bundle.stable}\n{bundle.volatile}"
    assert bundle.estimated_tokens > 0
    assert "grass_type: TTTF" in bundle.stable
    # The manual-irrigation framing is part of the water balance section.
    assert "operator-manual" in bundle.volatile


@pytest.mark.asyncio
async def test_honest_zero_inventory_is_distinct_from_untracked(client: AsyncClient) -> None:
    await _lawn(client)
    await client.post("/api/v1/products", json={
        "name": "GrubEx", "manufacturer": "Scotts", "product_type": "insecticide",
        "label_rate": 2.87, "label_rate_unit": "lb_per_1000",
        "current_inventory": 0, "current_inventory_unit": "lb",
    })
    await client.post("/api/v1/products", json={
        "name": "Mystery Granules", "manufacturer": "Acme", "product_type": "fertilizer_synthetic",
        "label_rate": 2.5, "label_rate_unit": "lb_per_1000",
    })
    bundle = await _build_bundle()

    products_section = bundle.stable.split("<products>")[1].split("</products>")[0]
    assert "current_inventory empty = untracked; 0 = a known zero" in products_section
    grubex_row = next(line for line in products_section.splitlines() if line.startswith("GrubEx"))
    assert ",0.0,lb," in grubex_row  # a known zero renders as 0.0, not blank
    mystery_row = next(line for line in products_section.splitlines() if line.startswith("Mystery"))
    assert ",,," in mystery_row  # untracked renders blank


@pytest.mark.asyncio
async def test_guardrail_findings_pass_through_verbatim(client: AsyncClient) -> None:
    """A live nitrogen caution from the guardrail service lands in the bundle
    with its code, severity, and numbers -- rendered, never recomputed."""
    await _lawn(client)
    product = (await client.post("/api/v1/products", json={
        "name": "Hot Urea", "manufacturer": "Acme", "product_type": "fertilizer_synthetic",
        "label_rate": 3.5, "label_rate_unit": "lb_per_1000",
        "guaranteed_analysis": {"total_nitrogen_pct": 32.0},
    })).json()
    # 3.5 lb/1000 at 32% N = 1.12 lb N/1000 -- over the seeded 1.0 lb 30-day limit.
    await client.post("/api/v1/treatments", json={
        "applied_at": datetime.now(UTC).isoformat(),
        "application_method": "granular", "applicator": "self", "area_treated_sqft": 47000,
        "products": [{"product_id": product["id"], "rate_applied": 3.5, "rate_unit": "lb_per_1000"}],
    })
    bundle = await _build_bundle()

    findings_section = bundle.volatile.split("<guardrail_findings>")[1].split("</guardrail_findings>")[0]
    assert "code: nitrogen_load_30d" in findings_section
    assert "severity: caution" in findings_section
    assert '"threshold": 1.0' in findings_section


@pytest.mark.asyncio
async def test_provider_requires_a_real_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_config, "anthropic_api_key", None)
    with pytest.raises(LLMError, match="not configured"):
        get_llm_provider()

    # The historical .env.example placeholder must fail loud, not reach the API.
    monkeypatch.setattr(app_config, "anthropic_api_key", "placeholder-not-used-in-phase-1")
    with pytest.raises(LLMError, match="not configured"):
        get_llm_provider()


def test_system_prompt_loads_and_carries_the_binding_rules() -> None:
    prompt = load_system_prompt()
    assert "label" in prompt.lower()
    assert "cannot_evaluate" in prompt
    assert "read-only" in prompt.lower()
    # The prompt stays generic; lawn specifics live in the context bundle.
    assert "Topeka" not in prompt
