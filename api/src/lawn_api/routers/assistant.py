"""Read-only assistant chat.

Every request rebuilds the system prompt + full context bundle and replays the
conversation's recent turns; nothing model-facing is persisted. The user
message is flushed but only committed together with the assistant reply, so a
failed model call leaves no half-conversation behind -- the UI keeps the text
in the input and the operator retries.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from lawn_api.db import get_db
from lawn_api.integrations.llm import LLMError, get_llm_provider
from lawn_api.models.entities import AssistantConversation, AssistantMessage
from lawn_api.prompts import load_system_prompt
from lawn_api.schemas.assistant import (
    AssistantConversationKind,
    AssistantConversationOut,
    AssistantConversationSummary,
    ChatRequest,
    ChatResponse,
)
from lawn_api.services.context_bundle import build_context_bundle

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

# Prompt history window, in messages (user + assistant alternate, so 20
# messages = the last 10 exchanges). No summarization machinery: beyond the
# window, older turns simply fall out of the prompt while staying in the DB.
MAX_HISTORY_MESSAGES = 20

TITLE_MAX_CHARS = 80


def _title_from(message: str) -> str:
    first_line = message.strip().splitlines()[0]
    return first_line[:TITLE_MAX_CHARS]


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    try:
        provider = get_llm_provider()
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if payload.conversation_id is not None:
        conversation = await db.get(AssistantConversation, payload.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = AssistantConversation(kind="chat", title=_title_from(payload.message))
        db.add(conversation)
        await db.flush()

    user_message = AssistantMessage(
        conversation_id=conversation.id,
        role="user",
        content=payload.message.strip(),
    )
    db.add(user_message)
    await db.flush()

    history = (
        (
            await db.execute(
                select(AssistantMessage)
                .where(AssistantMessage.conversation_id == conversation.id)
                .order_by(AssistantMessage.seq.desc())
                .limit(MAX_HISTORY_MESSAGES)
            )
        )
        .scalars()
        .all()
    )
    messages = [{"role": m.role, "content": m.content} for m in reversed(history)]

    bundle = await build_context_bundle(db, datetime.now(UTC))
    try:
        response = await provider.complete(
            system=[
                {
                    "type": "text",
                    "text": f"{load_system_prompt()}\n\n{bundle.stable}",
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": bundle.volatile},
            ],
            messages=messages,
        )
    except LLMError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    reply = AssistantMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response.text,
        input_tokens=response.input_tokens + response.cache_read_tokens + response.cache_creation_tokens,
        output_tokens=response.output_tokens,
    )
    db.add(reply)
    conversation.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(reply)

    return ChatResponse(conversation_id=conversation.id, reply=reply, truncated=response.truncated)


@router.get("/conversations", response_model=list[AssistantConversationSummary])
async def list_conversations(
    kind: AssistantConversationKind | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[AssistantConversationSummary]:
    q = select(AssistantConversation).order_by(AssistantConversation.updated_at.desc())
    if kind is not None:
        q = q.where(AssistantConversation.kind == kind)
    return list((await db.execute(q)).scalars())


@router.get("/conversations/{conversation_id}", response_model=AssistantConversationOut)
async def get_conversation(
    conversation_id: UUID, db: AsyncSession = Depends(get_db)
) -> AssistantConversationOut:
    conversation = (
        await db.execute(
            select(AssistantConversation)
            .options(selectinload(AssistantConversation.messages))
            .where(AssistantConversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    conversation = await db.get(AssistantConversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conversation)
    await db.commit()
