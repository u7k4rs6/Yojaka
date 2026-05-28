from __future__ import annotations

from prompts.archetypes.judge import SYSTEM_PROMPT

from agents.base import AgentExecutor


class JudgeAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
