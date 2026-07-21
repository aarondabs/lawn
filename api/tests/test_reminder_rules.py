"""Reminder rule engine tests."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from lawn_api.db import AsyncSessionLocal
from lawn_api.models.entities import Reminder, WeatherObservation
from lawn_api.services.reminder_rules import TAG_MOW, evaluate_reminder_rules


async def _set_soil_temp(temp_f: float) -> None:
    async with AsyncSessionLocal() as db:
        db.add(WeatherObservation(observed_at=datetime.now(UTC), source="openmeteo", soil_temp_f=temp_f))
        await db.commit()


async def _open_reminder_count() -> int:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(select(func.count()).select_from(Reminder).where(Reminder.completed.is_(False)))
        ).scalar_one()


@pytest.mark.asyncio
async def test_mow_overdue_creates_one_reminder(client: AsyncClient) -> None:
    """Overdue mow in the growing season creates a reminder, once."""
    await _set_soil_temp(70)  # growing
    await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": (datetime.now(UTC) - timedelta(days=15)).isoformat(),
            "practice_type": "mow",
        },
    )

    async with AsyncSessionLocal() as db:
        created = await evaluate_reminder_rules(db)
    assert len(created) == 1
    assert TAG_MOW in created[0].description

    # Idempotent: a second run with the condition still true adds nothing.
    async with AsyncSessionLocal() as db:
        again = await evaluate_reminder_rules(db)
    assert again == []
    assert await _open_reminder_count() == 1


@pytest.mark.asyncio
async def test_mow_not_overdue_no_reminder(client: AsyncClient) -> None:
    await _set_soil_temp(70)
    await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": (datetime.now(UTC) - timedelta(days=3)).isoformat(),
            "practice_type": "mow",
        },
    )
    async with AsyncSessionLocal() as db:
        created = await evaluate_reminder_rules(db)
    assert created == []


@pytest.mark.asyncio
async def test_no_mow_reminder_when_dormant(client: AsyncClient) -> None:
    """Below the growing soil temp, an overdue mow does not fire -- grass is dormant."""
    await _set_soil_temp(42)  # dormant
    await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
            "practice_type": "mow",
        },
    )
    async with AsyncSessionLocal() as db:
        created = await evaluate_reminder_rules(db)
    assert created == []


@pytest.mark.asyncio
async def test_evaluate_reminders_endpoint(client: AsyncClient) -> None:
    await _set_soil_temp(70)
    await client.post(
        "/api/v1/cultural-practices",
        json={
            "performed_at": (datetime.now(UTC) - timedelta(days=20)).isoformat(),
            "practice_type": "mow",
        },
    )
    r = await client.post("/api/v1/admin/evaluate-reminders")
    assert r.status_code == 200
    assert len(r.json()["created"]) == 1
