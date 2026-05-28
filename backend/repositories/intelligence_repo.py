from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import IntelligenceRecord, IntelligenceType, Team
from storage.models import IntelligenceRecordRow


def _row_to_record(row: IntelligenceRecordRow) -> IntelligenceRecord:
    return IntelligenceRecord(
        id=UUID(row.id),
        session_id=UUID(row.session_id),
        debate_id=UUID(row.debate_id),
        type=IntelligenceType(row.type),
        team=Team(row.team),
        agent_role=row.agent_role,
        content=row.content or "",
        confidence=row.confidence or 0.0,
        scope=row.scope,
        created_at=row.created_at,
    )


class IntelligenceRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def insert(self, record: IntelligenceRecord) -> IntelligenceRecord:
        row = IntelligenceRecordRow(
            id=str(record.id),
            session_id=str(record.session_id),
            debate_id=str(record.debate_id),
            type=record.type.value if isinstance(record.type, IntelligenceType) else record.type,
            team=record.team.value if isinstance(record.team, Team) else record.team,
            agent_role=record.agent_role,
            content=record.content,
            confidence=record.confidence,
            scope=record.scope,
            created_at=record.created_at,
        )
        self.db.add(row)
        # No flush here — called from fire-and-forget tasks that share the session;
        # the outer commit will persist all inserts together.
        return record

    async def list_for_debate(
        self, debate_id: str | UUID, team: Optional[Team] = None
    ) -> list[IntelligenceRecord]:
        stmt = (
            select(IntelligenceRecordRow)
            .where(IntelligenceRecordRow.debate_id == str(debate_id))
            .order_by(IntelligenceRecordRow.created_at.asc())
        )
        if team is not None:
            team_val = team.value if isinstance(team, Team) else team
            stmt = stmt.where(IntelligenceRecordRow.team == team_val)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_record(r) for r in rows]

    async def list_for_session(self, session_id: str | UUID) -> list[IntelligenceRecord]:
        result = await self.db.execute(
            select(IntelligenceRecordRow)
            .where(IntelligenceRecordRow.session_id == str(session_id))
            .order_by(IntelligenceRecordRow.created_at.asc())
        )
        rows = result.scalars().all()
        return [_row_to_record(r) for r in rows]
