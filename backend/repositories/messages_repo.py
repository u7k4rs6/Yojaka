from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import Message, Team
from storage.models import MessageRow


def _row_to_message(row: MessageRow) -> Message:
    metadata = json.loads(row.metadata_json) if row.metadata_json else {}
    return Message(
        id=UUID(row.id),
        session_id=UUID(row.session_id),
        debate_id=UUID(row.debate_id) if row.debate_id else None,
        stream_id=row.stream_id,
        role=row.role,
        team=Team(row.team) if row.team else None,
        content=row.content or "",
        round=row.round,
        phase=row.phase,
        model=row.model,
        temperature=row.temperature,
        tokens_in=row.tokens_in or 0,
        tokens_out=row.tokens_out or 0,
        cost_usd=row.cost_usd or 0.0,
        metadata=metadata,
        created_at=row.created_at,
    )


class MessagesRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def insert(self, msg: Message) -> Message:
        row = MessageRow(
            id=str(msg.id),
            session_id=str(msg.session_id),
            debate_id=str(msg.debate_id) if msg.debate_id else None,
            stream_id=msg.stream_id,
            role=msg.role,
            team=msg.team.value if msg.team else None,
            content=msg.content,
            round=msg.round,
            phase=msg.phase,
            model=msg.model,
            temperature=msg.temperature,
            tokens_in=msg.tokens_in,
            tokens_out=msg.tokens_out,
            cost_usd=msg.cost_usd,
            metadata_json=json.dumps(msg.metadata),
            created_at=msg.created_at,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return _row_to_message(row)

    async def list_for_session(self, session_id: str | UUID) -> list[Message]:
        result = await self.db.execute(
            select(MessageRow)
            .where(MessageRow.session_id == str(session_id))
            .order_by(MessageRow.created_at.asc())
        )
        rows = result.scalars().all()
        return [_row_to_message(r) for r in rows]

    async def list_for_debate(self, debate_id: str | UUID) -> list[Message]:
        result = await self.db.execute(
            select(MessageRow)
            .where(MessageRow.debate_id == str(debate_id))
            .order_by(MessageRow.created_at.asc())
        )
        rows = result.scalars().all()
        return [_row_to_message(r) for r in rows]

    async def get(self, message_id: str | UUID) -> Optional[Message]:
        result = await self.db.execute(
            select(MessageRow).where(MessageRow.id == str(message_id))
        )
        row = result.scalar_one_or_none()
        return _row_to_message(row) if row else None
