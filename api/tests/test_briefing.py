"""Briefing service tests. Provider and ntfy are faked; no real calls."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from test_assistant import FakeProvider

from lawn_api.integrations.llm import LLMError
from lawn_api.routers import assistant as assistant_router
from lawn_api.services import briefing as briefing_service

REPLY = "Water zones 1-3 for about 20 minutes each this morning; no rain before Thursday."


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    provider = FakeProvider(reply_text=REPLY)
    monkeypatch.setattr(briefing_service, "get_llm_provider", lambda: provider)
    return provider


@pytest.fixture
def ntfy_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    calls: list[dict] = []
    monkeypatch.setattr(briefing_service, "post_ntfy", lambda **kwargs: calls.append(kwargs))
    return calls


async def _run(now: datetime | None = None, force: bool = False) -> dict:
    from lawn_api.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return await briefing_service.run_briefing(db, now=now, force=force)


@pytest.mark.asyncio
async def test_briefing_persists_conversation_and_pushes_ntfy(
    client: AsyncClient, fake_provider: FakeProvider, ntfy_calls: list[dict]
) -> None:
    result = await _run()
    assert result["status"] == "sent"

    briefings = (await client.get("/api/v1/assistant/conversations?kind=briefing")).json()
    assert len(briefings) == 1
    assert briefings[0]["title"].startswith("Briefing — ")

    conv = (await client.get(f"/api/v1/assistant/conversations/{result['conversation_id']}")).json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]
    assert conv["messages"][1]["content"] == REPLY

    assert len(ntfy_calls) == 1
    push = ntfy_calls[0]
    assert push["topic"] == "lawn-briefings"
    assert push["message"] == REPLY
    assert push["title"].startswith("Lawn briefing")

    # Request shape: system prompt + stable bundle (cached), volatile bundle,
    # then the briefing instructions as the final system block.
    call = fake_provider.calls[0]
    assert len(call["system"]) == 3
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "Irrigation recommendation first" in call["system"][2]["text"]
    assert call["messages"] == [{"role": "user", "content": briefing_service.BRIEFING_REQUEST_MESSAGE}]


@pytest.mark.asyncio
async def test_frequency_off_skips(
    client: AsyncClient, fake_provider: FakeProvider, ntfy_calls: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def frequency_off(db, key, default):
        return "off"

    monkeypatch.setattr(briefing_service.app_settings, "get_str", frequency_off)
    result = await _run()
    assert result["status"] == "skipped"
    assert ntfy_calls == []
    assert fake_provider.calls == []


@pytest.mark.asyncio
async def test_weekly_fires_only_on_monday(
    client: AsyncClient, fake_provider: FakeProvider, ntfy_calls: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def frequency_weekly(db, key, default):
        return "weekly"

    monkeypatch.setattr(briefing_service.app_settings, "get_str", frequency_weekly)

    tuesday = datetime(2026, 9, 1, 18, 0, tzinfo=UTC)  # Tuesday in Central time
    assert (await _run(now=tuesday))["status"] == "skipped"

    monday = datetime(2026, 8, 31, 18, 0, tzinfo=UTC)  # Monday in Central time
    assert (await _run(now=monday))["status"] == "sent"
    assert len(ntfy_calls) == 1


@pytest.mark.asyncio
async def test_provider_failure_sends_nothing(
    client: AsyncClient, ntfy_calls: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom():
        raise LLMError("assistant not configured: set ANTHROPIC_API_KEY")

    monkeypatch.setattr(briefing_service, "get_llm_provider", boom)
    result = await _run()
    assert result["status"] == "error"
    assert "not configured" in result["reason"]
    assert ntfy_calls == []
    briefings = (await client.get("/api/v1/assistant/conversations")).json()
    assert briefings == []


@pytest.mark.asyncio
async def test_admin_trigger_bypasses_frequency(
    client: AsyncClient, fake_provider: FakeProvider, ntfy_calls: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def frequency_off(db, key, default):
        return "off"

    monkeypatch.setattr(briefing_service.app_settings, "get_str", frequency_off)
    r = await client.post("/api/v1/admin/run-briefing")
    assert r.status_code == 200
    assert r.json()["status"] == "sent"
    assert len(ntfy_calls) == 1


@pytest.mark.asyncio
async def test_briefing_is_continuable_as_chat(
    client: AsyncClient, fake_provider: FakeProvider, ntfy_calls: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    result = await _run()

    chat_provider = FakeProvider(reply_text="Hold off — rain is likely Thursday.")
    monkeypatch.setattr(assistant_router, "get_llm_provider", lambda: chat_provider)
    r = await client.post(
        "/api/v1/assistant/chat",
        json={"conversation_id": result["conversation_id"], "message": "Why zones 1-3 specifically?"},
    )
    assert r.status_code == 200

    replayed = chat_provider.calls[0]["messages"]
    assert replayed[0]["content"] == briefing_service.BRIEFING_REQUEST_MESSAGE
    assert replayed[1]["content"] == REPLY
    assert replayed[-1]["content"] == "Why zones 1-3 specifically?"
