from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import Session, SessionMode, SessionSettings
from storage.models import DebateRow, MessageRow, SessionRow


def _row_to_session(row: SessionRow) -> Session:
    settings_data = json.loads(row.settings_json) if row.settings_json else {}
    return Session(
        id=UUID(row.id),
        name=row.name,
        code=row.code,
        mode=SessionMode(row.mode),
        settings=SessionSettings(**settings_data),
        client_id=row.client_id or "",
        active_debate_id=UUID(row.active_debate_id) if row.active_debate_id else None,
        state=row.state or "idle",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SessionsRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        name: str,
        mode: str,
        settings: SessionSettings,
        client_id: str = "",
    ) -> Session:
        # Enforce max 10 sessions per client_id
        count_result = await self.db.execute(
            select(func.count()).select_from(SessionRow).where(
                SessionRow.client_id == client_id
            )
        )
        count = count_result.scalar_one()
        if count >= 10:
            raise HTTPException(
                status_code=409,
                detail="Only 10 chat sessions are allowed at a time.",
            )

        now = datetime.now(timezone.utc)
        row = SessionRow(
            id=str(uuid.uuid4()),
            name=name,
            code=None,
            mode=mode,
            settings_json=settings.model_dump_json(),
            client_id=client_id,
            active_debate_id=None,
            state="idle",
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return _row_to_session(row)

    async def get(self, session_id: str | UUID) -> Optional[Session]:
        result = await self.db.execute(
            select(SessionRow).where(SessionRow.id == str(session_id))
        )
        row = result.scalar_one_or_none()
        return _row_to_session(row) if row else None

    async def list_all(self, client_id: str = "") -> list[Session]:
        stmt = select(SessionRow).where(SessionRow.client_id == client_id).order_by(
            SessionRow.updated_at.desc()
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_session(r) for r in rows]

    async def rename(self, session_id: str | UUID, name: str) -> Session:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(SessionRow)
            .where(SessionRow.id == str(session_id))
            .values(name=name, updated_at=now)
        )
        await self.db.flush()
        session = await self.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        return session

    async def delete(self, session_id: str | UUID) -> None:
        await self.db.execute(
            delete(SessionRow).where(SessionRow.id == str(session_id))
        )
        await self.db.flush()

    async def delete_all(self, client_id: str = "") -> int:
        result = await self.db.execute(
            select(func.count()).select_from(SessionRow).where(
                SessionRow.client_id == client_id
            )
        )
        count = result.scalar_one()
        await self.db.execute(
            delete(SessionRow).where(SessionRow.client_id == client_id)
        )
        await self.db.flush()
        return count

    async def update_settings(
        self, session_id: str | UUID, settings: SessionSettings
    ) -> Session:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(SessionRow)
            .where(SessionRow.id == str(session_id))
            .values(settings_json=settings.model_dump_json(), updated_at=now)
        )
        await self.db.flush()
        session = await self.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        return session

    async def set_active_debate(
        self, session_id: str | UUID, debate_id: str | UUID | None
    ) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(SessionRow)
            .where(SessionRow.id == str(session_id))
            .values(
                active_debate_id=str(debate_id) if debate_id else None,
                updated_at=now,
            )
        )
        await self.db.flush()

    async def clear_history(self, session_id: str | UUID) -> None:
        # Delete all messages and debates for this session
        await self.db.execute(
            delete(MessageRow).where(MessageRow.session_id == str(session_id))
        )
        await self.db.execute(
            delete(DebateRow).where(DebateRow.session_id == str(session_id))
        )
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(SessionRow)
            .where(SessionRow.id == str(session_id))
            .values(active_debate_id=None, updated_at=now)
        )
        await self.db.flush()

    async def clear_memory(self, session_id: str | UUID) -> None:
        # Hard-delete cascade: deleting the session removes all related rows
        # via the cascade="all, delete-orphan" relationship config.
        await self.db.execute(
            delete(SessionRow).where(SessionRow.id == str(session_id))
        )
        await self.db.flush()
