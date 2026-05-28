from __future__ import annotations

from prompts.archetypes.cross_examiner import SYSTEM_PROMPT

from agents.base import AgentExecutor


class CrossExaminerAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
