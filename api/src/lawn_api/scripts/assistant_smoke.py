"""One-shot end-to-end assistant check (Phase 3 Task 1 verification).

Builds the real context bundle from the live DB, sends one question to the
configured provider, and prints the answer plus token usage. Makes a real,
billable API call -- run it deliberately, not from tests.

Usage, inside the api container:

    docker compose exec api python -m lawn_api.scripts.assistant_smoke \
        "When did I last apply nitrogen, and how much can I still apply this month?"

The request shape here -- system prompt + stable bundle under one cache
breakpoint, volatile bundle after it, question as the sole user message -- is
the same assembly the chat endpoint (Task 2) and briefing job (Task 3) use.
"""

import asyncio
import sys
from datetime import UTC, datetime

from lawn_api.db import AsyncSessionLocal
from lawn_api.integrations.llm import get_llm_provider
from lawn_api.prompts import load_system_prompt
from lawn_api.services.context_bundle import build_context_bundle

DEFAULT_QUESTION = "When did I last apply nitrogen, and how much can I still apply this month?"


async def run(question: str) -> None:
    async with AsyncSessionLocal() as db:
        bundle = await build_context_bundle(db, datetime.now(UTC))
    print(
        f"[bundle] {len(bundle.stable)} chars stable + {len(bundle.volatile)} chars volatile, "
        f"~{bundle.estimated_tokens} tokens estimated",
        file=sys.stderr,
    )

    provider = get_llm_provider()
    response = await provider.complete(
        system=[
            {
                "type": "text",
                "text": f"{load_system_prompt()}\n\n{bundle.stable}",
                "cache_control": {"type": "ephemeral"},
            },
            {"type": "text", "text": bundle.volatile},
        ],
        messages=[{"role": "user", "content": question}],
    )

    print(response.text)
    print(
        f"\n[usage] model={response.model} input={response.input_tokens} output={response.output_tokens} "
        f"cache_read={response.cache_read_tokens} cache_write={response.cache_creation_tokens}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    asyncio.run(run(" ".join(sys.argv[1:]) or DEFAULT_QUESTION))
