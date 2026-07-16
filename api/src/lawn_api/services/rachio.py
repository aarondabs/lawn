import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.config import settings
from lawn_api.integrations.rachio import (
    fetch_person_details,
    fetch_person_info,
    fetch_recent_events,
)
from lawn_api.models.entities import IrrigationEvent, IrrigationZone

logger = logging.getLogger(__name__)

RACHIO_SOURCE = "rachio"

HEAD_TYPE_MAP = {
    "spray": "spray",
    "rotor": "rotor",
    "fixed": "spray",
    "mp": "mp_rotator",
    "drip": "drip",
}

SUN_EXPOSURE_MAP = {
    "full sun": "full_sun",
    "part sun": "partial_sun",
    "part shade": "partial_shade",
    "full shade": "full_shade",
}

SLOPE_MAP = {
    "flat": "flat",
    "slight": "mild",
    "moderate": "moderate",
    "steep": "steep",
}

SOIL_TYPE_MAP = {
    "sand": "sand",
    "sandy loam": "sandy_loam",
    "loam": "loam",
    "silty loam": "silty_loam",
    "silty clay loam": "silty_clay_loam",
    "clay loam": "clay_loam",
    "clay": "clay",
}

SOIL_TYPE_MAP_V2 = {
    "sand": "sand",
    "sandy_loam": "sandy_loam",
    "loam": "loam",
    "silty_loam": "silty_loam",
    "silty_clay_loam": "silty_clay_loam",
    "clay_loam": "clay_loam",
    "clay": "clay",
}

SLOPE_MAP_V2 = {
    "zero_three": "flat",
    "three_six": "mild",
    "six_twelve": "moderate",
    "thirteen_plus": "steep",
}

SUN_EXPOSURE_MAP_V2 = {
    "lots_of_sun": "full_sun",
    "some_shade": "partial_sun",
    "mostly_shade": "partial_shade",
    "all_shade": "full_shade",
}


class RachioConfigError(RuntimeError):
    pass


ZONE_COMPLETED_SUMMARY_RE = re.compile(
    r"zone\s+(?P<zone_number>\d+)\s+completed\s+watering.*?for\s+(?P<minutes>\d+)\s+minute",
    re.IGNORECASE,
)


def _require_api_key() -> str:
    if not settings.rachio_api_key:
        raise RachioConfigError("RACHIO_API_KEY is not configured")
    return settings.rachio_api_key


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        # Rachio timestamps are typically epoch milliseconds.
        if value > 10_000_000_000:
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(UTC)
    return datetime.now(UTC)


def _zone_defaults(zone_payload: dict[str, Any]) -> dict[str, Any]:
    custom_shade = zone_payload.get("customShade") or {}
    custom_slope = zone_payload.get("customSlope") or {}
    custom_soil = zone_payload.get("customSoil") or {}
    return {
        "head_type": HEAD_TYPE_MAP.get(_norm(zone_payload.get("zoneType")), "rotor"),
        "sun_exposure": SUN_EXPOSURE_MAP.get(
            _norm(zone_payload.get("sunlightExposure")), "full_sun"
        )
        if zone_payload.get("sunlightExposure")
        else SUN_EXPOSURE_MAP_V2.get(_norm(custom_shade.get("name")), "full_sun"),
        "slope": SLOPE_MAP.get(_norm(zone_payload.get("slope")), "flat")
        if zone_payload.get("slope")
        else SLOPE_MAP_V2.get(_norm(custom_slope.get("name")), "flat"),
        "soil_type_override": SOIL_TYPE_MAP.get(_norm(zone_payload.get("soilType")))
        if zone_payload.get("soilType")
        else SOIL_TYPE_MAP_V2.get(_norm(custom_soil.get("name"))),
    }


def _extract_precip_rate(zone_payload: dict[str, Any]) -> float | None:
    legacy_rate = zone_payload.get("nozzleInchesPerHour")
    if legacy_rate is not None:
        return float(legacy_rate)

    custom_nozzle = zone_payload.get("customNozzle") or {}
    nozzle_rate = custom_nozzle.get("inchesPerHour")
    if nozzle_rate is None:
        return None

    efficiency = zone_payload.get("efficiency")
    if efficiency is None:
        return float(nozzle_rate)
    return float(nozzle_rate) * float(efficiency)


def _extract_zone_sqft(zone_payload: dict[str, Any]) -> int | None:
    if zone_payload.get("areaSqFt") is not None:
        return int(zone_payload["areaSqFt"])
    if zone_payload.get("yardAreaSquareFeet") is not None:
        return int(zone_payload["yardAreaSquareFeet"])
    return None


def _derive_zone_category(zone_payload: dict[str, Any]) -> str:
    if not bool(zone_payload.get("enabled", True)):
        return "inactive"

    crop_name = _norm((zone_payload.get("customCrop") or {}).get("name"))
    if "tree" in crop_name or "shrub" in crop_name:
        return "trees_shrubs"
    if "flower" in crop_name or "ornamental" in crop_name or "bed" in crop_name:
        return "ornamental"
    return "turf"


def _extract_zone_and_duration_from_summary(summary: Any) -> tuple[int | None, int | None]:
    if not isinstance(summary, str) or not summary:
        return None, None
    match = ZONE_COMPLETED_SUMMARY_RE.search(summary)
    if not match:
        return None, None
    zone_number = int(match.group("zone_number"))
    duration_seconds = int(match.group("minutes")) * 60
    return zone_number, duration_seconds


def _normalize_event_source(event: dict[str, Any]) -> str:
    """Map Rachio event fields to a value in IRRIGATION_EVENT_SOURCES."""
    subtype = _norm(event.get("subType"))
    summary = _norm(event.get("summary"))

    if "quick run" in summary or "quick_run" in subtype:
        return "rachio_quick_run"
    if "manual" in subtype or "manual" in summary:
        return "rachio_manual"
    if "schedule" in subtype or "schedule" in summary:
        return "rachio_scheduled"
    return "rachio_scheduled"


async def sync_rachio_zones(db: AsyncSession) -> dict[str, Any]:
    api_key = _require_api_key()
    person = await fetch_person_info(api_key)

    devices = person.get("devices")
    if not isinstance(devices, list) or len(devices) == 0:
        person_id = person.get("id")
        if person_id:
            # person/info may omit full device+zone payload; person/{id} includes it.
            person = await fetch_person_details(api_key, person_id)

    updated_count = 0
    created_count = 0

    for device in person.get("devices", []):
        for zone in device.get("zones", []):
            rachio_zone_id = zone.get("id")
            if not rachio_zone_id:
                continue

            existing = (
                await db.execute(
                    select(IrrigationZone).where(IrrigationZone.rachio_zone_id == rachio_zone_id)
                )
            ).scalar_one_or_none()

            defaults = _zone_defaults(zone)
            incoming_precip = _extract_precip_rate(zone)
            incoming_category = _derive_zone_category(zone)

            payload = {
                "rachio_zone_id": rachio_zone_id,
                "is_enabled": bool(zone.get("enabled", True)),
                "zone_category": incoming_category,
                "zone_number": int(zone.get("zoneNumber") or 0),
                "name": zone.get("name") or f"Zone {zone.get('zoneNumber', '?')}",
                "sqft": _extract_zone_sqft(zone),
                "head_type": defaults["head_type"],
                "nozzle_gpm": zone.get("gpm"),
                "sun_exposure": defaults["sun_exposure"],
                "slope": defaults["slope"],
                "soil_type_override": defaults["soil_type_override"],
                "notes": zone.get("description"),
            }

            if existing is None:
                payload["precipitation_rate_in_per_hr"] = incoming_precip
                db.add(IrrigationZone(**payload))
                created_count += 1
                continue

            for key, value in payload.items():
                setattr(existing, key, value)

            # Preserve manual non-turf overrides when Rachio metadata says turf.
            if existing.zone_category not in {"turf", "inactive"} and incoming_category == "turf":
                existing.zone_category = existing.zone_category
            else:
                existing.zone_category = incoming_category

            # Preserve local precip calibration if it is already set.
            if existing.precipitation_rate_in_per_hr is None:
                existing.precipitation_rate_in_per_hr = incoming_precip

            updated_count += 1

    await db.commit()

    return {
        "status": "ok",
        "source": RACHIO_SOURCE,
        "zones_created": created_count,
        "zones_updated": updated_count,
    }


async def poll_rachio_events(db: AsyncSession, lookback_hours: int = 24) -> dict[str, Any]:
    api_key = _require_api_key()

    has_zones = (
        await db.execute(select(exists().where(IrrigationZone.rachio_zone_id.is_not(None))))
    ).scalar_one()
    if not has_zones:
        return {
            "status": "skipped",
            "reason": "no_rachio_zones_connected",
            "events_processed": 0,
            "events_inserted": 0,
        }

    person = await fetch_person_info(api_key)
    person_id = person.get("id")
    if not person_id:
        raise RuntimeError("Rachio person id missing from person/info response")

    person_details = await fetch_person_details(api_key, person_id)
    device_ids = [
        str(device.get("id"))
        for device in person_details.get("devices", [])
        if device.get("id")
    ]

    events: list[dict[str, Any]] = []
    for device_id in device_ids:
        device_events = await fetch_recent_events(
            api_key=api_key,
            device_id=device_id,
            lookback_hours=lookback_hours,
        )
        if device_events:
            events.extend(device_events)

    processed = 0
    inserted = 0

    for event in events:
        zone_external_id = event.get("zoneId")
        summary_zone_number, summary_duration_seconds = _extract_zone_and_duration_from_summary(
            event.get("summary")
        )

        zone = None
        if zone_external_id:
            zone = (
                await db.execute(
                    select(IrrigationZone).where(
                        IrrigationZone.rachio_zone_id == zone_external_id,
                        IrrigationZone.is_enabled.is_(True),
                    )
                )
            ).scalar_one_or_none()
        elif summary_zone_number is not None:
            zone = (
                await db.execute(
                    select(IrrigationZone).where(
                        IrrigationZone.zone_number == summary_zone_number,
                        IrrigationZone.is_enabled.is_(True),
                    )
                )
            ).scalar_one_or_none()

        if zone is None:
            continue

        source = _normalize_event_source(event)

        event_at = _to_datetime(event.get("eventDate") or event.get("createdDate"))
        rachio_event_id = event.get("id")

        already_exists = False
        if rachio_event_id:
            already_exists = (
                await db.execute(
                    select(
                        exists().where(IrrigationEvent.rachio_event_id == rachio_event_id)
                    )
                )
            ).scalar_one()
        if already_exists:
            continue

        duration_seconds = int(
            event.get("duration")
            or event.get("durationSeconds")
            or summary_duration_seconds
            or 0
        )
        if duration_seconds <= 0:
            continue

        started_at = event_at
        if summary_duration_seconds:
            # Summary events provide completion timestamp; convert to a start timestamp.
            started_at = event_at - timedelta(seconds=duration_seconds)

        precip_snapshot = Decimal(str(zone.precipitation_rate_in_per_hr or 0))

        db.add(
            IrrigationEvent(
                started_at=started_at,
                zone_id=zone.id,
                rachio_event_id=rachio_event_id,
                duration_seconds=max(duration_seconds, 0),
                precip_rate_in_per_hr_snapshot=precip_snapshot,
                source=source,
                skipped=bool(event.get("skipped", False)),
                skip_reason=event.get("skipReason"),
            )
        )
        processed += 1
        inserted += 1

    await db.commit()

    return {
        "status": "ok",
        "source": RACHIO_SOURCE,
        "events_processed": processed,
        "events_inserted": inserted,
    }


async def should_schedule_rachio_polling() -> bool:
    if not settings.rachio_api_key:
        return False
    return True
