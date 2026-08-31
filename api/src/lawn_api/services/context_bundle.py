"""Structured context assembly for the Phase 3 assistant.

The entire dataset fits in a prompt (~12k tokens measured 2026-08-05), so there
is no retrieval system by decision: every call gets the complete, precisely
computed picture. Sections are tagged text, split into two parts:

- `stable`  -- profile, equipment, products, soil tests, zones, full treatment
  and mow history, settings. Changes only when the operator logs something, so
  it sits before the prompt-cache breakpoint.
- `volatile` -- current date, weather, forecast, water balance, guardrail
  findings, open reminders. Changes every call and comes after the breakpoint.

Deterministic services stay authoritative: guardrail findings, water balance,
GDD and coverage numbers are rendered verbatim from the services that computed
them -- the assistant explains these numbers, it never recomputes them, and
`cannot_evaluate` passes through as-is. Derived treatment rows are reused from
the CSV export service so nitrogen/amount math stays in one place.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.models.entities import (
    AppSetting,
    Equipment,
    IrrigationEvent,
    IrrigationSkip,
    IrrigationZone,
    LawnProfile,
    Reminder,
    SoilTest,
    WeatherDaily,
    WeatherForecast,
)
from lawn_api.services.agronomy import gdd_accumulation, soil_temperature_trend
from lawn_api.services.export import (
    CULTURAL_FIELDS,
    PRODUCT_FIELDS,
    TREATMENT_FIELDS,
    WEATHER_FIELDS,
    cultural_rows,
    product_rows,
    rows_to_csv,
    treatment_rows,
)
from lawn_api.services.guardrails import evaluate_current_state
from lawn_api.services.localtime import CENTRAL, local_today
from lawn_api.services.water_balance import compute_water_balance

logger = logging.getLogger(__name__)

WEATHER_DAILY_WINDOW_DAYS = 30
RECENT_IRRIGATION_DAYS = 14


@dataclass
class ContextBundle:
    stable: str
    volatile: str

    @property
    def full(self) -> str:
        return f"{self.stable}\n{self.volatile}"

    @property
    def estimated_tokens(self) -> int:
        # Dense numeric CSV tokenizes at roughly 1.6 chars/token (measured on
        # the first live call: 18.3k chars -> 11.7k tokens), nothing like prose's
        # ~4. chars/2 keeps the estimate conservative; the real count comes back
        # in API usage fields and is logged per call by integrations/llm.py.
        return len(self.full) // 2


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(float(value))
    return str(value)


def _kv_lines(pairs: list[tuple[str, object]]) -> str:
    return "\n".join(f"{key}: {_fmt(value)}" for key, value in pairs)


def _section(tag: str, body: str) -> str:
    return f"<{tag}>\n{body.strip()}\n</{tag}>"


def _json(obj: object) -> str:
    # sort_keys keeps the stable part byte-stable across calls (cache prefix).
    return json.dumps(obj, sort_keys=True, separators=(", ", ": "))


async def _profile_section(db: AsyncSession) -> tuple[str, int | None]:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    if profile is None:
        return _section("lawn_profile", "no lawn profile recorded"), None
    body = _kv_lines(
        [
            ("total_sqft", profile.total_sqft),
            ("grass_type", profile.grass_type),
            ("usda_zone", profile.usda_zone),
            ("latitude", profile.latitude),
            ("longitude", profile.longitude),
            ("soil_type", profile.soil_type),
            ("water_source", profile.water_source),
            ("target_mow_height_inches", profile.target_mow_height_inches),
            ("establishment_date", profile.establishment_date),
            ("climate_notes", profile.climate_notes),
        ]
    )
    return _section("lawn_profile", body), profile.total_sqft


async def _equipment_section(db: AsyncSession) -> str:
    rows = (await db.execute(select(Equipment).order_by(Equipment.type, Equipment.make))).scalars().all()
    if not rows:
        return _section("equipment", "no equipment recorded")
    entries = []
    for e in rows:
        entries.append(
            _kv_lines(
                [
                    ("type", e.type),
                    ("make_model", f"{e.make} {e.model}"),
                    ("calibration", _json(e.calibration) if e.calibration else None),
                    ("last_calibration_date", e.last_calibration_date),
                    ("notes", e.notes),
                ]
            )
        )
    return _section("equipment", "\n---\n".join(entries))


async def _soil_test_section(db: AsyncSession) -> str:
    rows = (await db.execute(select(SoilTest).order_by(SoilTest.sample_date))).scalars().all()
    if not rows:
        return _section("soil_tests", "no soil tests recorded")
    entries = []
    for s in rows:
        entries.append(
            _kv_lines(
                [
                    ("sample_date", s.sample_date),
                    ("lab_name", s.lab_name),
                    ("ph", s.ph),
                    ("organic_matter_pct", s.organic_matter_pct),
                    ("phosphorus_ppm", s.phosphorus_ppm),
                    ("potassium_ppm", s.potassium_ppm),
                    ("calcium_ppm", s.calcium_ppm),
                    ("magnesium_ppm", s.magnesium_ppm),
                    ("sulfur_ppm", s.sulfur_ppm),
                    ("iron_ppm", s.iron_ppm),
                    ("manganese_ppm", s.manganese_ppm),
                    ("zinc_ppm", s.zinc_ppm),
                    ("copper_ppm", s.copper_ppm),
                    ("boron_ppm", s.boron_ppm),
                    ("cec", s.cec),
                    ("base_saturation", _json(s.base_saturation) if s.base_saturation else None),
                    ("lab_recommendations", s.lab_recommendations),
                    ("notes", s.notes),
                ]
            )
        )
    return _section("soil_tests", "\n---\n".join(entries))


ZONE_FIELDS = [
    "zone_number", "name", "zone_category", "sqft", "head_type",
    "precipitation_rate_in_per_hr", "sun_exposure", "slope", "is_enabled", "notes",
]


async def _zones_section(db: AsyncSession) -> str:
    zones = (await db.execute(select(IrrigationZone).order_by(IrrigationZone.zone_number))).scalars().all()
    rows = [
        {
            "zone_number": z.zone_number,
            "name": z.name,
            "zone_category": z.zone_category,
            "sqft": z.sqft,
            "head_type": z.head_type,
            "precipitation_rate_in_per_hr": float(z.precipitation_rate_in_per_hr)
            if z.precipitation_rate_in_per_hr is not None
            else None,
            "sun_exposure": z.sun_exposure,
            "slope": z.slope,
            "is_enabled": z.is_enabled,
            "notes": z.notes,
        }
        for z in zones
    ]
    body = (
        "precipitation_rate_in_per_hr converts watering minutes to inches applied.\n"
        + rows_to_csv(rows, ZONE_FIELDS)
    )
    return _section("irrigation_zones", body)


async def _settings_section(db: AsyncSession) -> str:
    rows = (await db.execute(select(AppSetting).order_by(AppSetting.key))).scalars().all()
    lines = [
        f"{row.key} = {_json(row.value)}" + (f"  # {row.description}" if row.description else "")
        for row in rows
    ]
    return _section("app_settings", "\n".join(lines) if lines else "no settings recorded")


async def _forecast_rows(db: AsyncSession, today) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(WeatherForecast)
                .where(WeatherForecast.forecast_for_day >= today)
                .order_by(WeatherForecast.forecast_for_day.asc(), WeatherForecast.fetched_at.desc())
            )
        )
        .scalars()
        .all()
    )
    # One row per day: the most recently fetched wins.
    by_day: dict[object, WeatherForecast] = {}
    for row in rows:
        by_day.setdefault(row.forecast_for_day, row)
    return [
        {
            "date": f.forecast_for_day.isoformat(),
            "temp_high_f": float(f.temp_high_f) if f.temp_high_f is not None else None,
            "temp_low_f": float(f.temp_low_f) if f.temp_low_f is not None else None,
            "precip_probability_pct": float(f.precip_probability_pct)
            if f.precip_probability_pct is not None
            else None,
            "precip_amount_in": float(f.precip_amount_in) if f.precip_amount_in is not None else None,
            "wind_mph": float(f.wind_mph) if f.wind_mph is not None else None,
            "conditions": f.conditions,
        }
        for f in by_day.values()
    ]


FORECAST_FIELDS = [
    "date", "temp_high_f", "temp_low_f", "precip_probability_pct",
    "precip_amount_in", "wind_mph", "conditions",
]

IRRIGATION_RECENT_FIELDS = [
    "started_at", "zone_name", "zone_category", "minutes", "inches_applied", "source", "skipped", "skip_reason",
]


async def _recent_irrigation_section(db: AsyncSession, now: datetime) -> str:
    since = now - timedelta(days=RECENT_IRRIGATION_DAYS)
    events = (
        await db.execute(
            select(IrrigationEvent, IrrigationZone.name, IrrigationZone.zone_category)
            .join(IrrigationZone, IrrigationZone.id == IrrigationEvent.zone_id)
            .where(IrrigationEvent.started_at >= since)
            .order_by(IrrigationEvent.started_at)
        )
    ).all()
    rows = [
        {
            "started_at": e.started_at.isoformat(),
            "zone_name": name,
            "zone_category": category,
            "minutes": round(e.duration_seconds / 60, 1),
            "inches_applied": float(e.inches_applied),
            "source": e.source,
            "skipped": e.skipped,
            "skip_reason": e.skip_reason,
        }
        for e, name, category in events
    ]
    skips = (
        (
            await db.execute(
                select(IrrigationSkip).where(IrrigationSkip.occurred_at >= since).order_by(IrrigationSkip.occurred_at)
            )
        )
        .scalars()
        .all()
    )
    skip_lines = [f"{s.occurred_at.isoformat()} [{s.subtype}] {s.summary}" for s in skips]
    body = (
        f"events, last {RECENT_IRRIGATION_DAYS} days:\n"
        + rows_to_csv(rows, IRRIGATION_RECENT_FIELDS)
        + f"\nRachio schedule skips, last {RECENT_IRRIGATION_DAYS} days:\n"
        + ("\n".join(skip_lines) if skip_lines else "none")
    )
    return _section("recent_irrigation", body)


def _findings_body(findings: list) -> str:
    if not findings:
        return "no outstanding cautions"
    entries = []
    for f in findings:
        entries.append(
            _kv_lines(
                [
                    ("code", f.code),
                    ("severity", f.severity),
                    ("title", f.title),
                    ("message", f.message),
                    ("numbers", _json(f.numbers)),
                    ("product", f.product_name),
                ]
            )
        )
    return "\n---\n".join(entries)


async def _reminders_section(db: AsyncSession) -> str:
    rows = (
        (
            await db.execute(
                select(Reminder).where(Reminder.completed.is_(False)).order_by(Reminder.due_date.asc())
            )
        )
        .scalars()
        .all()
    )
    lines = [f"{r.due_date.isoformat()} [{r.reminder_type}] {r.description}" for r in rows]
    return _section("open_reminders", "\n".join(lines) if lines else "none")


async def build_context_bundle(db: AsyncSession, now: datetime | None = None) -> ContextBundle:
    """Assemble the full assistant context. See the module docstring for the
    stable/volatile split; callers place the cache breakpoint between them."""
    now = now or datetime.now(UTC)
    today = local_today(now)

    profile_section, lawn_sqft = await _profile_section(db)

    products = await product_rows(db, lawn_sqft)
    products_body = (
        "current_inventory empty = untracked; 0 = a known zero (out of stock).\n"
        + rows_to_csv(products, PRODUCT_FIELDS)
    )

    stable_parts = [
        profile_section,
        await _equipment_section(db),
        _section("products", products_body),
        await _soil_test_section(db),
        await _zones_section(db),
        _section("treatments", rows_to_csv(await treatment_rows(db), TREATMENT_FIELDS)),
        _section("cultural_practices", rows_to_csv(await cultural_rows(db), CULTURAL_FIELDS)),
        await _settings_section(db),
    ]

    weather_since = today - timedelta(days=WEATHER_DAILY_WINDOW_DAYS)
    weather_rows = (
        (
            await db.execute(
                select(WeatherDaily)
                .where(WeatherDaily.observation_date >= weather_since)
                .order_by(WeatherDaily.observation_date)
            )
        )
        .scalars()
        .all()
    )
    weather_body = rows_to_csv(
        [
            {
                "observation_date": w.observation_date.isoformat(),
                "temp_high_f": float(w.temp_high_f) if w.temp_high_f is not None else None,
                "temp_low_f": float(w.temp_low_f) if w.temp_low_f is not None else None,
                "gdd_base50": float(w.gdd_base50) if w.gdd_base50 is not None else None,
                "precip_sum_in": float(w.precip_sum_in) if w.precip_sum_in is not None else None,
            }
            for w in weather_rows
        ],
        WEATHER_FIELDS,
    )

    water_balance = await compute_water_balance(db, now)
    water_body = (
        "Irrigation is operator-manual by choice: no automatic Rachio schedule runs. "
        "Watering decisions are made by the operator from rainfall and these numbers.\n"
        + _json(water_balance)
    )

    findings = await evaluate_current_state(db, now)

    volatile_parts = [
        _section(
            "current_datetime",
            f"{now.astimezone(CENTRAL).isoformat(timespec='minutes')} (lawn-local; today = {today.isoformat()})",
        ),
        _section(f"weather_daily_last_{WEATHER_DAILY_WINDOW_DAYS}d", weather_body),
        _section("gdd", _json(await gdd_accumulation(db, now))),
        _section("soil_temperature", _json(await soil_temperature_trend(db, now))),
        _section("forecast", rows_to_csv(await _forecast_rows(db, today), FORECAST_FIELDS)),
        _section("water_balance", water_body),
        await _recent_irrigation_section(db, now),
        _section("guardrail_findings", _findings_body(findings)),
        await _reminders_section(db),
    ]

    bundle = ContextBundle(stable="\n".join(stable_parts), volatile="\n".join(volatile_parts))
    logger.info(
        "context bundle assembled: %d chars stable + %d chars volatile, ~%d tokens estimated",
        len(bundle.stable),
        len(bundle.volatile),
        bundle.estimated_tokens,
    )
    return bundle
