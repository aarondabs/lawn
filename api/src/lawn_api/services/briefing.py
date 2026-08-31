"""Scheduled assistant briefing: the irrigation recommendation, pushed daily.

The centerpiece of Phase 3. A fixed prompt over the same context bundle as
chat; the result is pushed to the briefings ntfy topic and persisted as a
`kind='briefing'` conversation so it is reviewable — and continuable as a
normal chat — in the app.

Frequency is data, not deployment: `briefing_frequency` in app_setting
('daily' | 'weekly' | 'off', default daily; weekly fires Mondays) is read on
every run, so the operator can downgrade a noisy briefing with a settings row,
not a code change.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.config import settings
from lawn_api.integrations.llm import LLMError, get_llm_provider
from lawn_api.models.entities import AssistantConversation, AssistantMessage
from lawn_api.prompts import load_briefing_prompt, load_system_prompt
from lawn_api.services import settings as app_settings
from lawn_api.services.context_bundle import build_context_bundle
from lawn_api.services.localtime import local_today
from lawn_api.services.notifications import post_ntfy

logger = logging.getLogger(__name__)

# The stored user turn. Kept short and honest: the full briefing instructions
# are a versioned prompt file, not transcript content, and a conversation must
# open with a user message for the reply chain to stay replayable in chat.
BRIEFING_REQUEST_MESSAGE = "Give me today's lawn briefing."


async def run_briefing(db: AsyncSession, now: datetime | None = None, force: bool = False) -> dict:
    """Generate, persist, and push one briefing. Returns a status dict.

    `force=True` (the manual admin trigger) bypasses the frequency gate but
    everything else behaves identically to the scheduled run.
    """
    now = now or datetime.now(UTC)
    today = local_today(now)

    if not force:
        frequency = await app_settings.get_str(db, app_settings.BRIEFING_FREQUENCY, "daily")
        if frequency == "off":
            return {"status": "skipped", "reason": "briefing_frequency=off"}
        if frequency == "weekly" and today.weekday() != 0:
            return {"status": "skipped", "reason": "briefing_frequency=weekly, not Monday"}

    try:
        provider = get_llm_provider()
        bundle = await build_context_bundle(db, now)
        response = await provider.complete(
            system=[
                {
                    "type": "text",
                    "text": f"{load_system_prompt()}\n\n{bundle.stable}",
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": bundle.volatile},
                {"type": "text", "text": load_briefing_prompt()},
            ],
            messages=[{"role": "user", "content": BRIEFING_REQUEST_MESSAGE}],
        )
    except LLMError as exc:
        logger.error("briefing failed: %s", exc)
        return {"status": "error", "reason": str(exc)}

    conversation = AssistantConversation(kind="briefing", title=f"Briefing — {today.isoformat()}")
    db.add(conversation)
    await db.flush()
    db.add(
        AssistantMessage(
            conversation_id=conversation.id, role="user", content=BRIEFING_REQUEST_MESSAGE
        )
    )
    db.add(
        AssistantMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response.text,
            input_tokens=response.input_tokens + response.cache_read_tokens + response.cache_creation_tokens,
            output_tokens=response.output_tokens,
        )
    )
    await db.commit()

    # post_ntfy is sync urllib; keep it off the event loop.
    await asyncio.to_thread(
        post_ntfy,
        title=f"Lawn briefing — {today.strftime('%b %-d')}",
        message=response.text,
        tags="sun_with_face",
        topic=settings.ntfy_briefings_topic,
    )
    if response.truncated:
        logger.warning("briefing was truncated at the output limit")

    return {"status": "sent", "conversation_id": str(conversation.id)}
