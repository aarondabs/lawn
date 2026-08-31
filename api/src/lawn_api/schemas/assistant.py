from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from lawn_api.models.constants import ASSISTANT_CONVERSATION_KINDS, ASSISTANT_MESSAGE_ROLES

AssistantConversationKind = Literal[*ASSISTANT_CONVERSATION_KINDS]
AssistantMessageRole = Literal[*ASSISTANT_MESSAGE_ROLES]


class AssistantMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: AssistantMessageRole
    content: str
    created_at: datetime


class AssistantConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: AssistantConversationKind
    title: str | None
    created_at: datetime
    updated_at: datetime


class AssistantConversationOut(AssistantConversationSummary):
    messages: list[AssistantMessageOut]


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    conversation_id: UUID
    reply: AssistantMessageOut
    # True when the answer hit LLM_MAX_TOKENS mid-thought; the UI says so
    # rather than presenting a cut-off answer as complete.
    truncated: bool
