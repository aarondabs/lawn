"""LLM provider abstraction for the Phase 3 assistant.

One method matters: send a system prompt + messages, get a text response. The
Anthropic implementation lives behind LLMProvider so the provider is swappable
config, not architecture. The assistant is read-only by decision -- no tool use,
no function calling -- so the interface deliberately does not grow those knobs.

Failures raise LLMError with an operator-honest message; surfaces render it as
"assistant unavailable" rather than inventing an answer. Token usage is logged
per call from day one (the phase's cost-monitoring requirement).
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import anthropic

from lawn_api.config import settings

logger = logging.getLogger(__name__)

# 60s, not the SDK's 10-minute default: every surface is either a human watching
# a spinner or a scheduled job that should fail fast and log. The SDK retries
# 429/5xx and connection errors itself (max_retries=2 by default), so there is
# deliberately no hand-rolled retry loop here.
REQUEST_TIMEOUT_SECONDS = 60.0


class LLMError(Exception):
    """The assistant could not produce an answer.

    The message is safe to show the operator. Never catch this to substitute a
    made-up reply -- "assistant unavailable" is the honest rendering.
    """


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int


class LLMProvider(Protocol):
    async def complete(
        self,
        *,
        system: str | list[dict],
        messages: list[dict],
        max_tokens: int | None = None,
    ) -> LLMResponse: ...


class AnthropicProvider:
    """Anthropic Messages API. `system` may be a plain string or a list of
    content blocks, so callers can put a cache_control breakpoint after the
    stable context-bundle prefix (see services/context_bundle.py)."""

    def __init__(self, api_key: str, model: str, max_tokens: int):
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(
        self,
        *,
        system: str | list[dict],
        messages: list[dict],
        max_tokens: int | None = None,
    ) -> LLMResponse:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens or self._max_tokens,
                system=system,
                messages=messages,
            )
        except anthropic.APIStatusError as exc:
            logger.error("LLM call failed: HTTP %s from the model API: %s", exc.status_code, exc.message)
            raise LLMError("assistant unavailable: the model API returned an error") from exc
        except anthropic.APIConnectionError as exc:  # includes APITimeoutError
            logger.error("LLM call failed: could not reach the model API: %s", exc)
            raise LLMError("assistant unavailable: could not reach the model API") from exc

        usage = response.usage
        result = LLMResponse(
            text="".join(block.text for block in response.content if block.type == "text"),
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=usage.cache_read_input_tokens or 0,
            cache_creation_tokens=usage.cache_creation_input_tokens or 0,
        )
        logger.info(
            "LLM call: model=%s input=%d output=%d cache_read=%d cache_write=%d stop=%s",
            result.model,
            result.input_tokens,
            result.output_tokens,
            result.cache_read_tokens,
            result.cache_creation_tokens,
            response.stop_reason,
        )

        if not result.text:
            # A refusal or an empty completion is a failure to answer, not an
            # answer. Report it rather than returning an empty string a surface
            # might render as a blank bubble.
            raise LLMError(f"assistant returned no answer (stop_reason={response.stop_reason})")
        return result


def get_llm_provider() -> LLMProvider:
    """The configured provider, or LLMError if the assistant is not set up.

    Treats the historical .env.example placeholder as unconfigured so an old
    copied .env fails loud instead of sending a junk key to the API.
    """
    key = (settings.anthropic_api_key or "").strip()
    if not key or key.lower().startswith("placeholder"):
        raise LLMError("assistant not configured: set ANTHROPIC_API_KEY in .env and recreate the api container")
    return AnthropicProvider(api_key=key, model=settings.llm_model, max_tokens=settings.llm_max_tokens)
