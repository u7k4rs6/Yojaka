from __future__ import annotations

from prompts.archetypes.evidence_researcher import SYSTEM_PROMPT

from agents.base import AgentExecutor


class EvidenceResearcherAgent(AgentExecutor):
    SYSTEM_PROMPT = SYSTEM_PROMPT
