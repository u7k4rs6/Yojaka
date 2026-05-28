from __future__ import annotations

from prompts.archetypes.rebuttal_critic import SYSTEM_PROMPT

from agents.base import AgentExecutor


class RebuttalCriticAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
