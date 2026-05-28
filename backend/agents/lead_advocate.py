from __future__ import annotations

from prompts.archetypes.lead_advocate import SYSTEM_PROMPT

from agents.base import AgentExecutor


class LeadAdvocateAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
