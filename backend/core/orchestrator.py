from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from core.schemas import (
    AgentAssignment, AgentSettings, Archetype, CouncilSettings, Debate, DebateStatus,
    Message, Session, SessionMode, SessionSettings, Team,
)
from core.phase_scheduler import Phase, PhaseGraphBuilder
from core.safety_guard import SafetyGuard
from budget.session_budget import BudgetExhausted, SessionBudget
from budget.accountant import TokenAccountant
from budget.tokenizer import estimate_tokens
from events.stream_manager import StreamManager
from memory.manager import MemoryManager
from memory.context_window import ContextWindow
from providers.router import ProviderRouter
from providers.utility_tier import UtilityTier
from repositories.debates_repo import DebatesRepo
from repositories.messages_repo import MessagesRepo
from repositories.sessions_repo import SessionsRepo
from repositories.intelligence_repo import IntelligenceRepo
from repositories.user_profile_repo import UserProfileRepo
from repositories.runtime_diary_repo import RuntimeDiaryRepo
from agents import ARCHETYPE_MAP, AgentExecutor
from analytics.engine import AnalyticsEngine
from config import settings

logger = logging.getLogger(__name__)


class DebateOrchestrator:
    def __init__(
        self,
        *,
        sessions_repo:   SessionsRepo,
        debates_repo:    DebatesRepo,
        messages_repo:   MessagesRepo,
        intelligence_repo: IntelligenceRepo,
        user_profile_repo: UserProfileRepo,
        diary_repo:      RuntimeDiaryRepo,
        stream_manager:  StreamManager,
        provider_router: ProviderRouter,
        utility_tier:    UtilityTier,
        council:         CouncilSettings,
    ) -> None:
        self.sessions_repo    = sessions_repo
        self.debates_repo     = debates_repo
        self.messages_repo    = messages_repo
        self.intelligence_repo = intelligence_repo
        self.user_profile_repo = user_profile_repo
        self.diary_repo       = diary_repo
        self.stream_manager   = stream_manager
        self.provider_router  = provider_router
        self.utility_tier     = utility_tier
        self.council          = council
        self.safety_guard     = SafetyGuard(utility_tier)
        self.scheduler        = PhaseGraphBuilder()

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _log(self, event: str, detail: str, session_id: Optional[UUID] = None) -> None:
        try:
            await self.diary_repo.log("backend terminal", event, detail, session_id)
        except Exception:
            logger.exception("diary write failed: %s", event)

    def _build_assignments(self, session: Session, model: str) -> list[AgentAssignment]:
        """Build the agent assignment list based on session settings."""
        s = session.settings
        n = s.debaters_per_team
        archetypes_per_slot = [
            Archetype.LEAD_ADVOCATE,
            Archetype.REBUTTAL_CRITIC,
            Archetype.EVIDENCE_RESEARCHER,
            Archetype.CROSS_EXAMINER,
        ]
        assignments: list[AgentAssignment] = []
        for i in range(min(n, 4)):
            arch = archetypes_per_slot[i]
            for team in (Team.PRO, Team.CON):
                assignments.append(AgentAssignment(
                    team=team, archetype=arch, slot=min(i, 2),
                    model=model, settings=s.agent_settings.get(arch.value) or AgentSettings(),
                ))
        # Judge
        assignments.append(AgentAssignment(
            team=Team.NEUTRAL, archetype=Archetype.JUDGE,
            slot=0, model=model,
        ))
        if s.judge_assistant_enabled:
            assignments.append(AgentAssignment(
                team=Team.NEUTRAL, archetype=Archetype.JUDGE_ASSISTANT,
                slot=0, model=model,
            ))
        return assignments

    def _make_agent(
        self,
        assignment: AgentAssignment,
        debate: Debate,
        budget: SessionBudget,
        accountant: TokenAccountant,
        context_window: ContextWindow,
        memory_manager: MemoryManager,
    ) -> AgentExecutor:
        cls = ARCHETYPE_MAP.get(assignment.archetype.value, AgentExecutor)
        return cls(
            assignment=assignment,
            context_window=context_window,
            memory_manager=memory_manager,
            budget=budget,
            accountant=accountant,
            stream_manager=self.stream_manager,
            provider_router=self.provider_router,
            intelligence_repo=self.intelligence_repo,
            diary=self.diary_repo,
            debate=debate,
            council=self.council,
        )

    async def _check_consensus(self, topic: str, messages: list[Message]) -> bool:
        """Ask utility tier for early consensus. Returns True if consensus detected."""
        if not messages:
            return False
        recent = " ".join(m.content[:200] for m in messages[-4:])
        try:
            answer = await self.utility_tier.ask_yes_no(
                f"Have the debaters reached consensus on the topic '{topic}'? Reply YES or NO.",
                context=recent,
            )
            return answer == "YES"
        except Exception:
            return False

    # ── Main debate runner ────────────────────────────────────────────────────

    async def run_debate(
        self,
        session: Session,
        topic: str,
        model: str,
        client_id: str = "",
    ) -> None:
        """Full AI vs AI debate flow. Broadcasts WS events via stream_manager."""
        await self._log("debate_started", f"topic={topic}", session.id)

        assignments = self._build_assignments(session, model)
        debate = await self.debates_repo.create(
            session_id=session.id,
            topic=topic,
            mode=session.mode,
            assignments=assignments,
        )

        budget     = SessionBudget(session.id, cap=settings.session_token_budget)
        accountant = TokenAccountant(
            rates_repo=None,   # cost_rates_repo injected separately in prod
            events_repo=None,  # token_events_repo injected separately
        )
        context_window = ContextWindow(max_turns=settings.context_window_turns)
        from memory.semantic import SemanticMemory
        from memory.experience import ExperienceMemory
        from memory.user_profile import UserProfileMemory
        from repositories.agent_experience_repo import AgentExperienceRepo
        from repositories.cost_rates_repo import CostRatesRepo
        from repositories.token_events_repo import TokenEventsRepo
        # These repos need their own DB session (we reuse the orchestrator's session)
        # Since the orchestrator already owns db-scoped repos, we need to create new ones
        # The orchestrator's session is managed outside, so we pass an appropriate repo
        semantic   = SemanticMemory()
        # For dev: use the same DB as the orchestrator via a new in-debate scope
        # ExperienceMemory with a real repo - we need to create it with the session
        # We'll pass intelligence_repo session — use a wrapper approach
        experience = ExperienceMemory(None)  # populated below if available
        user_prof  = UserProfileMemory(self.user_profile_repo)
        memory_mgr = MemoryManager(context_window, semantic, experience, user_prof)

        # Positions
        pro_pos = f"This house believes: {topic}"
        con_pos = f"This house does not believe: {topic}"

        # Broadcast debate_started
        await self.stream_manager.broadcast({
            "type":           "debate_started",
            "debate":         debate.model_dump(mode="json"),
            "topic":          topic,
            "positions":      {"pro": pro_pos, "con": con_pos},
            "selected_model": model,
            "assignments":    [a.model_dump(mode="json") for a in assignments],
            "judge":          {},
            "active_debates": 1,
        })

        phases = self.scheduler.build(debate)
        analytics = AnalyticsEngine()
        all_messages: list[Message] = []
        early_stop_reason: Optional[str] = None

        try:
            for phase in phases:
                if early_stop_reason:
                    break

                if phase.execution == "PARALLEL":
                    tasks = [
                        self._run_phase_turn(
                            phase, a, debate, budget, accountant,
                            context_window, memory_mgr,
                        )
                        for a in phase.participants
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for r in results:
                        if isinstance(r, BudgetExhausted):
                            early_stop_reason = "budget_exhausted"
                            break
                        if isinstance(r, Message):
                            all_messages.append(r)
                            await analytics.update_bayesian(
                                await analytics.analyze_turn(r, all_messages[:-1])
                            )
                else:
                    for assignment in phase.participants:
                        try:
                            msg = await self._run_phase_turn(
                                phase, assignment, debate, budget, accountant,
                                context_window, memory_mgr,
                            )
                            all_messages.append(msg)
                            await analytics.update_bayesian(
                                await analytics.analyze_turn(msg, all_messages[:-1])
                            )
                        except BudgetExhausted:
                            early_stop_reason = "budget_exhausted"
                            break

                if early_stop_reason:
                    break

                # Consensus check after discussion phases
                if phase.type == "discussion" and not early_stop_reason:
                    if await self._check_consensus(topic, all_messages):
                        early_stop_reason = "consensus"
                        await self._log("early_consensus", f"debate={debate.id}", session.id)

            if early_stop_reason:
                await self.stream_manager.broadcast({
                    "type":       "early_stop",
                    "reason":     early_stop_reason,
                    "tokens_used": budget.consumed,
                    "debate_id":  str(debate.id),
                })
                await self.debates_repo.update_status(debate.id, DebateStatus.EARLY_STOPPED)
            else:
                await self.debates_repo.update_status(debate.id, DebateStatus.COMPLETED)

        except Exception as exc:
            logger.exception("orchestrator crash: %s", exc)
            await self._log("debate_failed", str(exc), session.id)
            await self.debates_repo.update_status(debate.id, DebateStatus.EARLY_STOPPED)
            await self.stream_manager.broadcast({"type": "error", "message": str(exc)})
            return

        # Finalize analytics
        try:
            analytics_payload = await analytics.finalize(debate.id, [])
            await self.debates_repo.attach_analytics(debate.id, analytics_payload)
        except Exception:
            analytics_payload = {}

        await self._log("debate_completed", f"debate={debate.id}", session.id)
        await self.stream_manager.broadcast({
            "type":           "debate_completed",
            "debate_id":      str(debate.id),
            "judge_summary":  analytics_payload,
            "active_debates": 0,
            "cost_summary":   {"tokens_used": budget.consumed},
        })

    async def _run_phase_turn(
        self,
        phase: Phase,
        assignment: AgentAssignment,
        debate: Debate,
        budget: SessionBudget,
        accountant: TokenAccountant,
        context_window: ContextWindow,
        memory_mgr: MemoryManager,
    ) -> Message:
        agent = self._make_agent(assignment, debate, budget, accountant, context_window, memory_mgr)
        return await agent.execute_turn(phase, round_number=phase.round_number)

    # ── Practice / interaction runner ─────────────────────────────────────────

    async def run_interaction(
        self,
        session: Session,
        topic: str,
        model: str,
        practice_side: Optional[str] = None,
    ) -> None:
        """Single-turn AI vs human interaction (practice mode)."""
        from core.practice_controller import PracticeController

        assignments = [
            AgentAssignment(
                team=Team.CON if practice_side == "pro" else Team.PRO,
                archetype=Archetype.PRACTICE_DEBATER,
                slot=0,
                model=model,
            )
        ]
        debate = await self.debates_repo.create(
            session_id=session.id,
            topic=topic,
            mode=SessionMode.AI_VS_HUMAN,
            assignments=assignments,
        )

        await self.stream_manager.broadcast({
            "type":           "interaction_started",
            "mode":           "ai_vs_human",
            "debate":         debate.model_dump(mode="json"),
            "selected_model": model,
        })

        budget     = SessionBudget(session.id, cap=settings.session_token_budget)
        accountant = TokenAccountant(rates_repo=None, events_repo=None)
        context_window = ContextWindow(max_turns=settings.context_window_turns)
        from memory.semantic import SemanticMemory
        from memory.experience import ExperienceMemory
        from memory.user_profile import UserProfileMemory
        semantic   = SemanticMemory()
        experience = ExperienceMemory(None)
        user_prof  = UserProfileMemory(self.user_profile_repo)
        memory_mgr = MemoryManager(context_window, semantic, experience, user_prof)

        try:
            phase = Phase(
                id=uuid4(), type="discussion", execution="SEQUENTIAL",
                dependencies=[], participants=assignments, round_number=1,
            )
            await self._run_phase_turn(
                phase, assignments[0], debate, budget, accountant,
                context_window, memory_mgr,
            )
        except BudgetExhausted:
            pass
        except Exception as exc:
            logger.exception("interaction error: %s", exc)
            await self.stream_manager.broadcast({"type": "error", "message": str(exc)})
            return

        await self.stream_manager.broadcast({
            "type":       "interaction_completed",
            "mode":       "ai_vs_human",
            "debate_id":  str(debate.id),
            "cost_summary": {"tokens_used": budget.consumed},
        })
