"""Typed access to app_setting.

Guardrails and reminder rules read their thresholds from here rather than from
hardcoded constants, so the operator can retune them without a code change. Each
getter takes a default used when the key is absent -- the seeded values (migration
d4f1a67c8e23) mean that should not happen in practice, but a guardrail must still
produce a number rather than crash if a row was deleted.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.models.entities import AppSetting

# Setting keys, named once so a typo is a NameError rather than a silent miss.
NITROGEN_30D = "nitrogen_lb_per_1000_per_30d"
NITROGEN_SEASON = "nitrogen_lb_per_1000_per_season"
PREEMERGENT_BLOCKING_DAYS_DEFAULT = "preemergent_blocking_days_default"
DAYS_SINCE_MOW_THRESHOLD = "days_since_mow_threshold"
SOIL_TEMP_PREEMERGENT_F = "soil_temp_preemergent_f"
# The month/day the annual-cumulative counters reset. Grub and N programs are
# seasonal, so "once per year" means "once per season", not once per Jan 1 --
# an operator applying a week earlier next year must not trip last year's cap.
SEASON_START_MONTH_DAY = "season_start_month_day"
# Date GDD accumulation starts from each year (spring green-up).
GDD_GREEN_UP_MONTH_DAY = "gdd_green_up_month_day"


async def get_all(db: AsyncSession) -> dict[str, object]:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    return {row.key: row.value for row in rows}


async def get_decimal(db: AsyncSession, key: str, default: Decimal) -> Decimal:
    row = await db.get(AppSetting, key)
    if row is None or row.value is None:
        return default
    try:
        return Decimal(str(row.value))
    except (ValueError, ArithmeticError):
        return default


async def get_int(db: AsyncSession, key: str, default: int) -> int:
    row = await db.get(AppSetting, key)
    if row is None or row.value is None:
        return default
    try:
        return int(row.value)
    except (ValueError, TypeError):
        return default


async def get_str(db: AsyncSession, key: str, default: str) -> str:
    row = await db.get(AppSetting, key)
    if row is None or row.value is None:
        return default
    return str(row.value)
