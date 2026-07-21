"""Rule-based reminder generation.

Evaluates a set of deterministic rules against recorded state and creates
reminder rows when a condition holds. The existing scheduled reminder check
(main.py) then notifies about anything due. Thresholds come from app_setting so
the operator can retune without a code change.

Idempotency without a schema change: each rule owns a stable tag embedded at the
end of its description. A rule creates a reminder only when no open (incomplete)
reminder already carries its tag, so a condition that persists for days yields
one reminder, not a daily pile. When the operator completes it (or the follow-up
that clears the condition), the rule is free to fire again next time.

Not here: anything needing a treatment calendar (a planned application's date
approaching). That calendar is Phase 3; this rule is intentionally omitted rather
than faked.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.models.entities import CulturalPractice, Reminder, WeatherObservation
from lawn_api.services import settings as app_settings

CENTRAL = ZoneInfo("America/Chicago")

# Stable, machine-matchable tags. Kept terse and appended to the human text.
TAG_MOW = "[rule:mow-overdue]"
TAG_PREEMERGENT = "[rule:preemergent-window]"

# Grass is not growing (and does not need mowing) below this soil temperature.
GROWING_SOIL_TEMP_F = 50.0


async def _has_open_reminder_with_tag(db: AsyncSession, tag: str) -> bool:
    return (
        await db.execute(
            select(
                select(Reminder.id)
                .where(Reminder.completed.is_(False), Reminder.description.like(f"%{tag}"))
                .exists()
            )
        )
    ).scalar_one()


async def _latest_soil_temp(db: AsyncSession) -> float | None:
    value = (
        await db.execute(
            select(WeatherObservation.soil_temp_f)
            .where(WeatherObservation.soil_temp_f.isnot(None))
            .order_by(WeatherObservation.observed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return float(value) if value is not None else None


async def _avg_soil_temp(db: AsyncSession, now: datetime, days: int) -> float | None:
    value = (
        await db.execute(
            select(func.avg(WeatherObservation.soil_temp_f)).where(
                WeatherObservation.observed_at >= now - timedelta(days=days),
                WeatherObservation.soil_temp_f.isnot(None),
            )
        )
    ).scalar_one_or_none()
    return float(value) if value is not None else None


async def _days_since_mow(db: AsyncSession, now: datetime) -> int | None:
    last = (
        await db.execute(
            select(func.max(CulturalPractice.performed_at)).where(CulturalPractice.practice_type == "mow")
        )
    ).scalar_one_or_none()
    return None if last is None else (now - last).days


def _season_window(today: date, start_md: str, end_md: str) -> bool:
    """True when today falls in the [start, end] month-day window of this year."""
    try:
        sm, sd = (int(p) for p in start_md.split("-"))
        em, ed = (int(p) for p in end_md.split("-"))
        return date(today.year, sm, sd) <= today <= date(today.year, em, ed)
    except (ValueError, TypeError):
        return False


async def _create(db: AsyncSession, reminder_type: str, description: str, due: date) -> Reminder:
    reminder = Reminder(reminder_type=reminder_type, description=description, due_date=due)
    db.add(reminder)
    return reminder


async def evaluate_reminder_rules(db: AsyncSession, now: datetime | None = None) -> list[Reminder]:
    """Create reminders for any rule whose condition holds and isn't already open."""
    now = now or datetime.now(tz=ZoneInfo("UTC"))
    today = now.astimezone(CENTRAL).date()
    created: list[Reminder] = []

    # --- Mow overdue -------------------------------------------------------
    # Only while the grass is growing -- a dormant lawn does not need mowing.
    soil_temp = await _latest_soil_temp(db)
    growing = soil_temp is not None and soil_temp > GROWING_SOIL_TEMP_F
    days_since_mow = await _days_since_mow(db, now)
    mow_threshold = await app_settings.get_int(db, app_settings.DAYS_SINCE_MOW_THRESHOLD, 10)

    if growing and days_since_mow is not None and days_since_mow > mow_threshold:
        if not await _has_open_reminder_with_tag(db, TAG_MOW):
            created.append(
                await _create(
                    db,
                    "cultural",
                    f"Time to mow — {days_since_mow} days since the last mow. {TAG_MOW}",
                    today,
                )
            )

    # --- Spring pre-emergent window ----------------------------------------
    # Soil temperature sustaining above the threshold in spring is the classic
    # pre-emergent timing signal for crabgrass.
    if _season_window(today, "02-15", "05-15"):
        threshold_f = await app_settings.get_decimal(db, app_settings.SOIL_TEMP_PREEMERGENT_F, Decimal("55"))
        avg = await _avg_soil_temp(db, now, days=5)
        if avg is not None and avg >= float(threshold_f):
            if not await _has_open_reminder_with_tag(db, TAG_PREEMERGENT):
                created.append(
                    await _create(
                        db,
                        "check",
                        (
                            f"Soil temp is averaging {avg:.0f}°F — the pre-emergent window is opening. "
                            f"Apply before germination. {TAG_PREEMERGENT}"
                        ),
                        today,
                    )
                )

    if created:
        await db.commit()
        for reminder in created:
            await db.refresh(reminder)
    return created
