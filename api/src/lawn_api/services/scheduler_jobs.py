"""APScheduler job bodies and registration.

Extracted from main.py's lifespan (which had grown three inline closures) when
the fourth job arrived. Each job opens its own session, catches everything,
and logs — a failed job must never take the scheduler down with it.
"""

import asyncio
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from lawn_api.db import AsyncSessionLocal
from lawn_api.services import settings as app_settings
from lawn_api.services.briefing import run_briefing
from lawn_api.services.notifications import post_ntfy
from lawn_api.services.rachio import poll_rachio_events, should_schedule_rachio_polling
from lawn_api.services.weather import refresh_weather

logger = logging.getLogger(__name__)


async def scheduled_weather_refresh() -> None:
    try:
        async with AsyncSessionLocal() as session:
            await refresh_weather(session)
    except Exception:
        logger.exception("Scheduled weather refresh failed")


async def scheduled_rachio_poll() -> None:
    try:
        async with AsyncSessionLocal() as session:
            await poll_rachio_events(session)
    except Exception:
        logger.exception("Scheduled Rachio polling failed")


async def scheduled_reminder_check() -> None:
    """Generate rule-based reminders, then notify about anything due."""
    from lawn_api.models.entities import Reminder
    from lawn_api.services.localtime import local_today
    from lawn_api.services.reminder_rules import evaluate_reminder_rules

    try:
        # Create reminders from the rules first, so newly-triggered ones are
        # included in the same run's notification.
        async with AsyncSessionLocal() as session:
            await evaluate_reminder_rules(session)

        today = local_today(datetime.now(UTC))
        async with AsyncSessionLocal() as session:
            reminders = (
                (
                    await session.execute(
                        select(Reminder)
                        .where(Reminder.completed.is_(False))
                        .where(Reminder.due_date <= today)
                        .order_by(Reminder.due_date.asc())
                    )
                )
                .scalars()
                .all()
            )

        if not reminders:
            return

        overdue = [r for r in reminders if r.due_date < today]
        due_today = [r for r in reminders if r.due_date == today]

        lines = []
        if due_today:
            lines.append(f"Due today ({len(due_today)}):")
            for r in due_today:
                lines.append(f"  • [{r.reminder_type}] {r.description}")
        if overdue:
            lines.append(f"Overdue ({len(overdue)}):")
            for r in overdue:
                lines.append(f"  • [{r.reminder_type}] {r.description} (was {r.due_date})")

        count = len(reminders)
        title = f"{count} lawn reminder{'s' if count != 1 else ''} pending"
        await asyncio.to_thread(
            post_ntfy, title=title, message="\n".join(lines), priority="default", tags="seedling"
        )
    except Exception:
        logger.exception("Scheduled reminder check failed")


async def scheduled_briefing() -> None:
    try:
        async with AsyncSessionLocal() as session:
            result = await run_briefing(session)
        logger.info("scheduled briefing: %s", result)
    except Exception:
        # run_briefing notifies on model failures itself; this catches the
        # unexpected (DB down, bundle bug) so the operator still hears about it.
        logger.exception("Scheduled briefing failed")
        await asyncio.to_thread(
            post_ntfy,
            title="Lawn briefing crashed",
            message="Unexpected error — see `docker logs lawn-api`.",
            priority="high",
            tags="warning",
        )


async def register_jobs(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        scheduled_weather_refresh,
        trigger="interval",
        hours=6,
        id="weather-refresh",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

    if await should_schedule_rachio_polling():
        scheduler.add_job(
            scheduled_rachio_poll,
            trigger="interval",
            hours=1,
            id="rachio-poll",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    # Daily reminder check at 8:00 AM local time (America/Chicago)
    scheduler.add_job(
        scheduled_reminder_check,
        trigger="cron",
        hour=8,
        minute=0,
        timezone="America/Chicago",
        id="reminder-check",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

    # Assistant briefing. Hour is a setting read at startup (restart to apply);
    # frequency (daily/weekly/off) is read inside the job on every run.
    async with AsyncSessionLocal() as session:
        briefing_hour = await app_settings.get_int(session, app_settings.BRIEFING_HOUR_LOCAL, 6)
    scheduler.add_job(
        scheduled_briefing,
        trigger="cron",
        hour=briefing_hour,
        minute=0,
        timezone="America/Chicago",
        id="assistant-briefing",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
