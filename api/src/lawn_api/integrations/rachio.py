from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

RACHIO_API_BASE = "https://api.rach.io/1/public"


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


async def fetch_person_info(api_key: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{RACHIO_API_BASE}/person/info",
            headers=_auth_headers(api_key),
        )
        response.raise_for_status()
        return response.json()


async def fetch_person_details(api_key: str, person_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{RACHIO_API_BASE}/person/{person_id}",
            headers=_auth_headers(api_key),
        )
        response.raise_for_status()
        return response.json()


async def fetch_recent_events(
    api_key: str,
    device_id: str,
    lookback_hours: int = 24,
) -> list[dict[str, Any]]:
    end_at = datetime.now(UTC)
    start_at = end_at - timedelta(hours=lookback_hours)

    params = {
        "startTime": int(start_at.timestamp() * 1000),
        "endTime": int(end_at.timestamp() * 1000),
        "sortDirection": "DESC",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{RACHIO_API_BASE}/device/{device_id}/event",
            headers=_auth_headers(api_key),
            params=params,
        )
        response.raise_for_status()
        payload = response.json()

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return payload["events"]
    return []
