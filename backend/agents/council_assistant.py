from __future__ import annotations

from prompts.archetypes.council_assistant import SYSTEM_PROMPT

from agents.base import AgentExecutor


class CouncilAssistantAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
