import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.services.rachio import RachioConfigError, poll_rachio_events, sync_rachio_zones

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["rachio"])


@router.post("/rachio/connect")
async def connect_rachio(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        return await sync_rachio_zones(db)
    except RachioConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/webhooks/rachio")
async def rachio_webhook(request: Request) -> dict[str, str]:
    payload = await request.json()
    logger.info("Received Rachio webhook", extra={"payload": payload})
    return {"status": "accepted"}


@router.post("/admin/poll-rachio")
async def poll_rachio_endpoint(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        return await poll_rachio_events(db)
    except RachioConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
