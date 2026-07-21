from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.schemas.guardrail import GuardrailFinding
from lawn_api.services.guardrails import evaluate_current_state

router = APIRouter(prefix="/api/v1/guardrails", tags=["guardrails"])


@router.get("/current", response_model=list[GuardrailFinding])
async def get_current_guardrails(db: AsyncSession = Depends(get_db)) -> list[GuardrailFinding]:
    """Outstanding cautions as the record stands, for the dashboard.

    Distinct from the save-time findings on a treatment response: this asks
    "am I currently over any budget?" with no new application proposed.
    """
    return await evaluate_current_state(db)
