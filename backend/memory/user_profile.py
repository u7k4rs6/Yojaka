from __future__ import annotations

from core.schemas import UserDebateProfile
from repositories.user_profile_repo import UserProfileRepo


class UserProfileMemory:
    """L4 user debate profile memory backed by UserProfileRepo."""

    def __init__(self, repo: UserProfileRepo) -> None:
        self._repo = repo

    async def get(self, user_id: str = "default") -> UserDebateProfile:
        """Fetch the profile for *user_id*, creating a blank one if absent."""
        return await self._repo.get(user_id)

    async def update(self, profile: UserDebateProfile) -> UserDebateProfile:
        """Persist changes to *profile* and return the refreshed record."""
        return await self._repo.update(profile)
