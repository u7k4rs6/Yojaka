from __future__ import annotations

from prompts.archetypes.judge_assistant import SYSTEM_PROMPT

from agents.base import AgentExecutor


class JudgeAssistantAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
