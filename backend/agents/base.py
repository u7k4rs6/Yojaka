from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from budget.session_budget import BudgetExhausted, SessionBudget
from budget.tokenizer import count_tokens, estimate_tokens
from budget.accountant import TokenAccountant
from core.schemas import (
    AgentAssignment,
    CouncilSettings,
    Debate,
    IntelligenceRecord,
    IntelligenceType,
    Message,
)
from events.stream_manager import StreamManager
from memory.context_window import ContextWindow
from memory.manager import MemoryManager
from providers.router import MODEL_TO_PROVIDER, ProviderRouter
from repositories.intelligence_repo import IntelligenceRepo

import prompts.phases.constructive as _constructive
import prompts.phases.cross_exam as _cross_exam
import prompts.phases.evidence as _evidence
import prompts.phases.discussion as _discussion
import prompts.phases.rebuttal as _rebuttal
import prompts.phases.closing as _closing
import prompts.phases.judgment as _judgment

if TYPE_CHECKING:
    from observability.runtime_diary import RuntimeDiary

logger = logging.getLogger(__name__)

# ── Keyword sets for intelligence extraction ──────────────────────────────────

EVIDENCE_MARKERS = frozenset({
    "according to", "study", "research", "data", "evidence",
    "shows that", "found that", "statistics", "percent", "%",
    "survey", "report", "published", "journal", "source",
})

REBUTTAL_MARKERS = frozenset({
    "however", "but", "contradict", "disprove", "flawed", "fallacy",
    "ignores", "overlooks", "fails to", "weak", "incorrect",
    "misleading", "wrong", "false", "rebuttal", "counter",
})

UNCERTAINTY_MARKERS = frozenset({"may", "might", "possibly", "unclear", "uncertain"})

_PHASE_PROMPT_MAP: dict[str, str] = {
    "constructive": _constructive.PROMPT,
    "cross_exam":   _cross_exam.PROMPT,
    "evidence":     _evidence.PROMPT,
    "discussion":   _discussion.PROMPT,
    "rebuttal":     _rebuttal.PROMPT,
    "closing":      _closing.PROMPT,
    "judgment":     _judgment.PROMPT,
}


class AgentExecutor:
    SYSTEM_PROMPT: str = ""

    def __init__(
        self,
        assignment: AgentAssignment,
        context_window: ContextWindow,
        memory_manager: MemoryManager,
        budget: SessionBudget,
        accountant: TokenAccountant,
        stream_manager: StreamManager,
        provider_router: ProviderRouter,
        intelligence_repo: IntelligenceRepo,
        diary: "RuntimeDiary",
        debate: Debate,
        council: CouncilSettings,
    ) -> None:
        self.assignment        = assignment
        self.context_window    = context_window
        self.memory_manager    = memory_manager
        self.budget            = budget
        self.accountant        = accountant
        self.stream_manager    = stream_manager
        self.provider_router   = provider_router
        self.intelligence_repo = intelligence_repo
        self.diary             = diary
        self.debate            = debate
        self.council           = council

    # ── Model / temperature helpers ───────────────────────────────────────────

    def _get_model(self) -> str:
        return (
            (self.assignment.settings.model if self.assignment.settings else None)
            or self.assignment.model
            or "mock-debate-model"
        )

    def _get_temperature(self) -> float:
        if self.assignment.settings and self.assignment.settings.temperature is not None:
            return self.assignment.settings.temperature
        return 0.55

    # ── execute_turn ──────────────────────────────────────────────────────────

    async def execute_turn(self, phase, round_number: int = 1) -> Message:
        """
        Full agent turn lifecycle:
        1. Retrieve memory
        2. Build system prompt (with experience injection)
        3. Build user prompt from phase type
        4. Assemble messages list
        5. Estimate input tokens
        6. Determine max output tokens
        7. Reserve budget
        8. Stream from provider
        9. Collect streamed message
        10. Count actual output tokens
        11. Charge budget
        12. Record token event
        13. Push message to context window
        14. Spawn background intelligence extraction
        15. Return message
        """
        topic     = self.debate.topic
        archetype = self.assignment.archetype.value

        # 1. Retrieve memory
        memory = await self.memory_manager.get_relevant(
            topic,
            scope="universal",
            archetype=archetype,
        )

        # 2. Build system prompt
        system_prompt = self.SYSTEM_PROMPT
        experiences   = memory.get("experience", [])
        if experiences:
            snippets = "\n".join(e.content for e in experiences[:3])
            system_prompt = system_prompt + "\n\nRelevant experience:\n" + snippets

        # 3. Build user prompt
        phase_type = getattr(phase, "type", None) or getattr(phase, "phase_type", None) or str(phase)
        raw_prompt = _PHASE_PROMPT_MAP.get(str(phase_type), str(phase_type))

        position = (
            self.debate.pro_position
            if self.assignment.team.value == "pro"
            else self.debate.con_position
        ) or self.assignment.team.value

        user_prompt = raw_prompt.format(
            topic=topic,
            position=position,
        )

        # 4. Build messages list
        messages: list[dict] = (
            [{"role": "system", "content": system_prompt}]
            + self.context_window.to_openai_messages()
            + [{"role": "user", "content": user_prompt}]
        )

        # 5. Estimate input tokens
        estimate_in = estimate_tokens(system_prompt + str(messages))

        # 6. Determine max output tokens
        _settings_max = self.assignment.settings.max_tokens if self.assignment.settings else None
        max_out: int = _settings_max if (_settings_max and _settings_max > 0) else 400

        # 7. Reserve budget
        reserved = await self.budget.reserve(estimate_in + max_out)
        if not reserved:
            raise BudgetExhausted("Budget exhausted")

        # 8 & 9. Stream and collect message
        model       = self._get_model()
        temperature = self._get_temperature()

        stream = self.provider_router.call(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_out,
        )

        message = await self.stream_manager.stream_to_message(
            stream,
            self.assignment,
            stream_id=str(uuid4()),
            session_id=self.debate.session_id,
            debate_id=self.debate.id,
            round_number=round_number,
        )

        # 10. Count actual output tokens
        actual_out = count_tokens(message.content)

        # 11. Charge budget
        await self.budget.charge(actual_out, reserved=max_out)

        # 12. Record token event
        provider_name = MODEL_TO_PROVIDER.get(model, "mock")
        agent_role    = f"{self.assignment.team.value}_{archetype}"

        await self.accountant.record(
            session_id=self.debate.session_id,
            debate_id=self.debate.id,
            message_id=message.id,
            agent_role=agent_role,
            model=model,
            provider=provider_name,
            tokens_in=estimate_in,
            tokens_out=actual_out,
        )

        # 13. Push message to context window
        self.context_window.push(message)

        # 14. Background intelligence extraction
        asyncio.create_task(self._extract_intelligence(message))

        # 15. Return
        return message

    # ── Intelligence extraction ────────────────────────────────────────────────

    async def _extract_intelligence(self, message: Message) -> None:
        """
        Scan each sentence in message.content and emit IntelligenceRecord entries:
        - EVIDENCE  if any EVIDENCE_MARKERS present
        - CHALLENGE if any REBUTTAL_MARKERS present
        - CLAIM     if sentence is >20 chars and none of the above matched
        - LOW_CONFIDENCE additionally if any UNCERTAINTY_MARKERS present
        """
        if not message.debate_id:
            return

        sentences = [s.strip() for s in message.content.split(". ") if s.strip()]
        now       = datetime.now(timezone.utc)
        base_args = dict(
            session_id=message.session_id,
            debate_id=message.debate_id,
            team=self.assignment.team,
            agent_role=message.role,
            scope="universal",
            created_at=now,
        )

        for sentence in sentences:
            lower = sentence.lower()
            intel_type: IntelligenceType | None = None
            confidence = 0.8

            if any(marker in lower for marker in EVIDENCE_MARKERS):
                intel_type = IntelligenceType.EVIDENCE
            elif any(marker in lower for marker in REBUTTAL_MARKERS):
                intel_type = IntelligenceType.CHALLENGE
            elif len(sentence) > 20:
                intel_type = IntelligenceType.CLAIM
                confidence = 0.7

            if intel_type is not None:
                record = IntelligenceRecord(
                    id=uuid4(),
                    type=intel_type,
                    content=sentence,
                    confidence=confidence,
                    **base_args,
                )
                try:
                    await self.intelligence_repo.insert(record)
                except Exception:
                    logger.exception("Failed to insert intelligence record")

            # Additional LOW_CONFIDENCE record when uncertainty language is present
            if any(marker in lower for marker in UNCERTAINTY_MARKERS):
                lc_record = IntelligenceRecord(
                    id=uuid4(),
                    type=IntelligenceType.LOW_CONFIDENCE,
                    content=sentence,
                    confidence=0.3,
                    **base_args,
                )
                try:
                    await self.intelligence_repo.insert(lc_record)
                except Exception:
                    logger.exception("Failed to insert low-confidence intelligence record")
