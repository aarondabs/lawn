import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlalchemy import text

from lawn_api.db import AsyncSessionLocal
from lawn_api.routers import (
    admin_router,
    cultural_practice_router,
    dashboard_router,
    equipment_router,
    irrigation_zone_router,
    lawn_profile_router,
    product_router,
    rachio_router,
    reminder_router,
    soil_test_router,
    treatment_router,
)
from lawn_api.services.notifications import post_ntfy
from lawn_api.services.rachio import poll_rachio_events, should_schedule_rachio_polling
from lawn_api.services.weather import refresh_weather

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = AsyncIOScheduler(timezone="UTC")

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
        """Notify about reminders that are due today or overdue."""
        from datetime import date

        from sqlalchemy import select

        from lawn_api.models.entities import Reminder

        try:
            today = date.today()
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
                    lines.append(f"  \u2022 [{r.reminder_type}] {r.description}")
            if overdue:
                lines.append(f"Overdue ({len(overdue)}):")
                for r in overdue:
                    lines.append(f"  \u2022 [{r.reminder_type}] {r.description} (was {r.due_date})")

            count = len(reminders)
            title = f"{count} lawn reminder{'s' if count != 1 else ''} pending"
            post_ntfy(title=title, message="\n".join(lines), priority="default", tags="seedling")
        except Exception:
            logger.exception("Scheduled reminder check failed")

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

    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Lawn API", lifespan=lifespan)

app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(rachio_router)
app.include_router(lawn_profile_router)
app.include_router(irrigation_zone_router)
app.include_router(equipment_router)
app.include_router(product_router)
app.include_router(cultural_practice_router)
app.include_router(treatment_router)
app.include_router(soil_test_router)
app.include_router(reminder_router)


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}
