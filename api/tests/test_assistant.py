"""Assistant chat endpoint tests.

The provider is faked at the router boundary -- no test calls the real API.
What matters here: conversation/message persistence, the history window, the
kind filter, and that a failed model call leaves no half-conversation behind.
"""

import pytest
from httpx import AsyncClient

from lawn_api.integrations.llm import LLMError, LLMResponse
from lawn_api.routers import assistant as assistant_router


class FakeProvider:
    def __init__(self, reply_text: str = "A grounded answer.", stop_reason: str = "end_turn"):
        self.reply_text = reply_text
        self.stop_reason = stop_reason
        self.calls: list[dict] = []

    async def complete(self, *, system, messages, max_tokens=None) -> LLMResponse:
        self.calls.append({"system": system, "messages": messages})
        return LLMResponse(
            text=self.reply_text,
            model="fake-model",
            input_tokens=1000,
            output_tokens=50,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            stop_reason=self.stop_reason,
        )


class FailingProvider:
    async def complete(self, *, system, messages, max_tokens=None) -> LLMResponse:
        raise LLMError("assistant unavailable: the model API returned an error")


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr(assistant_router, "get_llm_provider", lambda: provider)
    return provider


@pytest.mark.asyncio
async def test_chat_creates_conversation_and_persists_both_turns(
    client: AsyncClient, fake_provider: FakeProvider
) -> None:
    r = await client.post("/api/v1/assistant/chat", json={"message": "How is the lawn doing?"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"]["role"] == "assistant"
    assert body["reply"]["content"] == "A grounded answer."
    assert body["truncated"] is False

    conv = (await client.get(f"/api/v1/assistant/conversations/{body['conversation_id']}")).json()
    assert conv["kind"] == "chat"
    assert conv["title"] == "How is the lawn doing?"
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]

    # The provider saw the system prompt + bundle with a cache breakpoint on
    # the stable block, and the user turn as the sole message.
    call = fake_provider.calls[0]
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "<lawn_profile>" in call["system"][0]["text"]
    assert "<guardrail_findings>" in call["system"][1]["text"]
    assert call["messages"] == [{"role": "user", "content": "How is the lawn doing?"}]


@pytest.mark.asyncio
async def test_followup_replays_history_in_order(client: AsyncClient, fake_provider: FakeProvider) -> None:
    first = (await client.post("/api/v1/assistant/chat", json={"message": "First question"})).json()
    r = await client.post(
        "/api/v1/assistant/chat",
        json={"conversation_id": first["conversation_id"], "message": "Follow-up"},
    )
    assert r.status_code == 200

    replayed = fake_provider.calls[1]["messages"]
    assert [m["role"] for m in replayed] == ["user", "assistant", "user"]
    assert replayed[0]["content"] == "First question"
    assert replayed[-1]["content"] == "Follow-up"


@pytest.mark.asyncio
async def test_history_window_caps_replayed_messages(client: AsyncClient, fake_provider: FakeProvider) -> None:
    first = (await client.post("/api/v1/assistant/chat", json={"message": "turn 0"})).json()
    for i in range(1, 12):
        await client.post(
            "/api/v1/assistant/chat",
            json={"conversation_id": first["conversation_id"], "message": f"turn {i}"},
        )

    last_call = fake_provider.calls[-1]["messages"]
    assert len(last_call) == assistant_router.MAX_HISTORY_MESSAGES
    # The window keeps the most recent messages and ends with the new turn.
    assert last_call[-1]["content"] == "turn 11"
    assert last_call[0]["content"] != "turn 0"


@pytest.mark.asyncio
async def test_failed_model_call_leaves_no_half_conversation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assistant_router, "get_llm_provider", lambda: FailingProvider())
    r = await client.post("/api/v1/assistant/chat", json={"message": "Doomed question"})
    assert r.status_code == 503
    assert "assistant unavailable" in r.json()["detail"]

    conversations = (await client.get("/api/v1/assistant/conversations")).json()
    assert conversations == []


@pytest.mark.asyncio
async def test_unconfigured_assistant_is_503_not_a_crash(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_unconfigured():
        raise LLMError("assistant not configured: set ANTHROPIC_API_KEY")

    monkeypatch.setattr(assistant_router, "get_llm_provider", raise_unconfigured)
    r = await client.post("/api/v1/assistant/chat", json={"message": "Hello?"})
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"]


@pytest.mark.asyncio
async def test_kind_filter_separates_briefings_from_chats(
    client: AsyncClient, fake_provider: FakeProvider
) -> None:
    from lawn_api.db import AsyncSessionLocal
    from lawn_api.models.entities import AssistantConversation

    await client.post("/api/v1/assistant/chat", json={"message": "A chat"})
    async with AsyncSessionLocal() as db:
        db.add(AssistantConversation(kind="briefing", title="Morning briefing"))
        await db.commit()

    all_convs = (await client.get("/api/v1/assistant/conversations")).json()
    chats = (await client.get("/api/v1/assistant/conversations?kind=chat")).json()
    briefings = (await client.get("/api/v1/assistant/conversations?kind=briefing")).json()
    assert len(all_convs) == 2
    assert [c["kind"] for c in chats] == ["chat"]
    assert [c["kind"] for c in briefings] == ["briefing"]


@pytest.mark.asyncio
async def test_delete_conversation_cascades(client: AsyncClient, fake_provider: FakeProvider) -> None:
    body = (await client.post("/api/v1/assistant/chat", json={"message": "Ephemeral"})).json()
    r = await client.delete(f"/api/v1/assistant/conversations/{body['conversation_id']}")
    assert r.status_code == 204
    r = await client.get(f"/api/v1/assistant/conversations/{body['conversation_id']}")
    assert r.status_code == 404
