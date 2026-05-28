from __future__ import annotations

from typing import Literal

from core.schemas import AgentExperience
from repositories.agent_experience_repo import AgentExperienceRepo


class ExperienceMemory:
    """L3 agent experience retrieval backed by AgentExperienceRepo."""

    def __init__(self, repo: AgentExperienceRepo) -> None:
        self._repo = repo

    async def get_relevant(
        self,
        archetype: str,
        scope: Literal["universal", "chat"],
        limit: int = 5,
    ) -> list[AgentExperience]:
        """
        Fetch the most relevant stored experiences for *archetype*.

        ``scope="universal"`` pulls from the global AgentExperience table.
        ``scope="chat"`` is a no-op at this layer (session-scoped intelligence
        is fetched separately via the repo's ``fetch_session_scoped`` method);
        an empty list is returned so callers stay decoupled.
        """
        if self._repo is None:
            return []
        if scope == "universal":
            return await self._repo.fetch_by_archetype(archetype, limit=limit)
        # chat-scoped experience requires a debate_id — not available here
        return []

    async def save(self, exp: AgentExperience) -> AgentExperience:
        """Persist (upsert) a new or updated experience record."""
        if self._repo is None:
            return exp
        return await self._repo.upsert(exp)
