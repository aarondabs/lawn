"""Versioned prompt files for the assistant.

Prompts are repo files, not inline strings, so prompt changes are diffs. The
system prompt stays generic: the lawn's grass type, location, and area come
from the context bundle's lawn_profile section (the DB owns that data, and this
repo is publishable).
"""

from functools import cache
from pathlib import Path


@cache
def load_system_prompt() -> str:
    return (Path(__file__).parent / "assistant_system.md").read_text(encoding="utf-8")


@cache
def load_briefing_prompt() -> str:
    return (Path(__file__).parent / "briefing_prompt.md").read_text(encoding="utf-8")
