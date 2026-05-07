import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.services.rachio import RachioConfigError, poll_rachio_events, sync_rachio_zones

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["rachio"])


@router.post("/rachio/connect")
async def connect_rachio(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        sync_result = await sync_rachio_zones(db)
        poll_result = await poll_rachio_events(db, lookback_hours=168)
        return {
            **sync_result,
            "backfill": poll_result,
        }
    except RachioConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/webhooks/rachio")
async def rachio_webhook(request: Request) -> dict[str, str]:
    payload = await request.json()
    logger.info("Received Rachio webhook", extra={"payload": payload})
    return {"status": "accepted"}


@router.post("/admin/poll-rachio")
async def poll_rachio_endpoint(
    lookback_hours: int = Query(default=168, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await poll_rachio_events(db, lookback_hours=lookback_hours)
    except RachioConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
