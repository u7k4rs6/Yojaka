from __future__ import annotations

from agents.base import AgentExecutor
from agents.council_assistant import CouncilAssistantAgent
from agents.cross_examiner import CrossExaminerAgent
from agents.debate_trainer import DebateTrainerAgent
from agents.evidence_researcher import EvidenceResearcherAgent
from agents.judge import JudgeAgent
from agents.judge_assistant import JudgeAssistantAgent
from agents.lead_advocate import LeadAdvocateAgent
from agents.practice_debater import PracticeDebaterAgent
from agents.rebuttal_critic import RebuttalCriticAgent

ARCHETYPE_MAP: dict[str, type[AgentExecutor]] = {
    "lead_advocate":      LeadAdvocateAgent,
    "rebuttal_critic":    RebuttalCriticAgent,
    "evidence_researcher": EvidenceResearcherAgent,
    "cross_examiner":     CrossExaminerAgent,
    "judge":              JudgeAgent,
    "judge_assistant":    JudgeAssistantAgent,
    "council_assistant":  CouncilAssistantAgent,
    "practice_debater":   PracticeDebaterAgent,
    "debate_trainer":     DebateTrainerAgent,
}


def create_agent(archetype: str, **kwargs) -> AgentExecutor:
    cls = ARCHETYPE_MAP.get(archetype, AgentExecutor)
    return cls(**kwargs)


__all__ = [
    "AgentExecutor",
    "LeadAdvocateAgent",
    "RebuttalCriticAgent",
    "EvidenceResearcherAgent",
    "CrossExaminerAgent",
    "JudgeAgent",
    "JudgeAssistantAgent",
    "CouncilAssistantAgent",
    "PracticeDebaterAgent",
    "DebateTrainerAgent",
    "ARCHETYPE_MAP",
    "create_agent",
]
