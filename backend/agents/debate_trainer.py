from __future__ import annotations

from prompts.archetypes.debate_trainer import SYSTEM_PROMPT

from agents.base import AgentExecutor


class DebateTrainerAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
