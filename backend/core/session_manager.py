from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from core.schemas import Session, SessionMode, SessionSettings
from repositories.sessions_repo import SessionsRepo


class SessionManager:
    """High-level service layer over :class:`SessionsRepo`."""

    def __init__(self, sessions_repo: SessionsRepo) -> None:
        self._repo = sessions_repo

    async def get_or_404(self, session_id: UUID) -> Session:
        session = await self._repo.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    async def list_sessions(self, client_id: str) -> list[Session]:
        return await self._repo.list_all(client_id=client_id)

    async def create_session(
        self,
        name: str,
        mode: SessionMode,
        settings: SessionSettings,
        client_id: str,
    ) -> Session:
        return await self._repo.create(name, mode, settings, client_id)

    async def delete_session(self, session_id: UUID) -> None:
        await self._repo.delete(session_id)

    async def rename_session(self, session_id: UUID, name: str) -> Session:
        return await self._repo.rename(session_id, name)

    async def update_settings(
        self, session_id: UUID, settings: SessionSettings
    ) -> Session:
        return await self._repo.update_settings(session_id, settings)
