from __future__ import annotations

from typing import Literal, Optional

from core.schemas import AgentExperience, Message
from memory.context_window import ContextWindow
from memory.experience import ExperienceMemory
from memory.semantic import SemanticMemory
from memory.user_profile import UserProfileMemory


class MemoryManager:
    """
    Facade over all four memory layers.

    L1 — ContextWindow   (recent message sliding window)
    L2 — SemanticMemory  (word-overlap indexed text store)
    L3 — ExperienceMemory (agent archetype lessons from DB)
    L4 — UserProfileMemory (user debate profile from DB)
    """

    def __init__(
        self,
        context_window: ContextWindow,
        semantic: SemanticMemory,
        experience: ExperienceMemory,
        user_profile: UserProfileMemory,
    ) -> None:
        self.context_window = context_window
        self.semantic = semantic
        self.experience = experience
        self.user_profile = user_profile

    def push_message(self, message: Message) -> None:
        """Add *message* to L1 context window and L2 semantic store."""
        self.context_window.push(message)
        self.semantic.add(
            text=message.content,
            metadata={
                "message_id": str(message.id),
                "role": message.role,
                "session_id": str(message.session_id),
                "debate_id": str(message.debate_id) if message.debate_id else None,
                "round": message.round,
                "phase": message.phase,
            },
        )

    async def get_relevant(
        self,
        query: str,
        scope: Literal["universal", "chat"],  # must always be passed explicitly
        archetype: Optional[str] = None,
        top_k: int = 5,
    ) -> dict:
        """
        Aggregate relevant memory from L1 and L3.

        Returns::

            {
                "context":    list[dict],           # OpenAI-format messages from L1
                "experience": list[AgentExperience], # L3 results (empty if no archetype)
            }
        """
        context: list[dict] = self.context_window.to_openai_messages()

        experiences: list[AgentExperience] = []
        if archetype:
            experiences = await self.experience.get_relevant(
                archetype=archetype,
                scope=scope,
                limit=top_k,
            )

        return {"context": context, "experience": experiences}
