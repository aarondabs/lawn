import logging
from datetime import UTC, datetime
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


class RachioConfigError(RuntimeError):
    pass


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
    return {
        "head_type": HEAD_TYPE_MAP.get(_norm(zone_payload.get("zoneType")), "rotor"),
        "sun_exposure": SUN_EXPOSURE_MAP.get(
            _norm(zone_payload.get("sunlightExposure")), "full_sun"
        ),
        "slope": SLOPE_MAP.get(_norm(zone_payload.get("slope")), "flat"),
        "soil_type_override": SOIL_TYPE_MAP.get(_norm(zone_payload.get("soilType"))),
    }


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
            incoming_precip = zone.get("nozzleInchesPerHour")

            payload = {
                "rachio_zone_id": rachio_zone_id,
                "zone_number": int(zone.get("zoneNumber") or 0),
                "name": zone.get("name") or f"Zone {zone.get('zoneNumber', '?')}",
                "sqft": int(zone["areaSqFt"]) if zone.get("areaSqFt") is not None else None,
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
        if not zone_external_id:
            continue

        zone = (
            await db.execute(
                select(IrrigationZone).where(IrrigationZone.rachio_zone_id == zone_external_id)
            )
        ).scalar_one_or_none()
        if zone is None:
            continue

        source = _norm(event.get("source") or RACHIO_SOURCE)
        source = source if source in {"rachio", "manual", "calculated"} else RACHIO_SOURCE

        started_at = _to_datetime(event.get("eventDate") or event.get("createdDate"))
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

        duration_seconds = int(event.get("duration") or event.get("durationSeconds") or 0)
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


async def should_schedule_rachio_polling(db: AsyncSession) -> bool:
    if not settings.rachio_api_key:
        return False

    has_zones = (
        await db.execute(select(exists().where(IrrigationZone.rachio_zone_id.is_not(None))))
    ).scalar_one()
    if not has_zones:
        logger.warning(
            "RACHIO_API_KEY is configured but no Rachio zones are connected yet. "
            "Run /api/v1/rachio/connect first; polling not scheduled."
        )
        return False
    return True
