from __future__ import annotations

from prompts.archetypes.practice_debater import SYSTEM_PROMPT

from agents.base import AgentExecutor


class PracticeDebaterAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
