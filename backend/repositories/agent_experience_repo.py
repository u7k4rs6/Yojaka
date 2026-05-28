from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import AgentExperience, IntelligenceRecord, IntelligenceType, Team
from storage.models import AgentExperienceRow, IntelligenceRecordRow


def _row_to_experience(row: AgentExperienceRow) -> AgentExperience:
    return AgentExperience(
        id=UUID(row.id),
        agent_archetype=row.agent_archetype,
        lesson_type=row.lesson_type,
        content=row.content or "",
        confidence=row.confidence,
        use_count=row.use_count or 0,
        last_used_at=row.last_used_at,
        source_debate_id=UUID(row.source_debate_id) if row.source_debate_id else None,
        source_session_id=UUID(row.source_session_id) if row.source_session_id else None,
    )


def _row_to_intelligence(row: IntelligenceRecordRow) -> IntelligenceRecord:
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


class AgentExperienceRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(self, exp: AgentExperience) -> AgentExperience:
        result = await self.db.execute(
            select(AgentExperienceRow).where(AgentExperienceRow.id == str(exp.id))
        )
        existing = result.scalar_one_or_none()

        if existing:
            await self.db.execute(
                update(AgentExperienceRow)
                .where(AgentExperienceRow.id == str(exp.id))
                .values(
                    agent_archetype=exp.agent_archetype,
                    lesson_type=exp.lesson_type,
                    content=exp.content,
                    confidence=exp.confidence,
                    use_count=exp.use_count,
                    last_used_at=exp.last_used_at,
                    source_debate_id=str(exp.source_debate_id) if exp.source_debate_id else None,
                    source_session_id=str(exp.source_session_id) if exp.source_session_id else None,
                )
            )
            await self.db.flush()
        else:
            row = AgentExperienceRow(
                id=str(exp.id),
                agent_archetype=exp.agent_archetype,
                lesson_type=exp.lesson_type,
                content=exp.content,
                confidence=exp.confidence,
                use_count=exp.use_count,
                last_used_at=exp.last_used_at,
                source_debate_id=str(exp.source_debate_id) if exp.source_debate_id else None,
                source_session_id=str(exp.source_session_id) if exp.source_session_id else None,
                embedding_blob=None,
            )
            self.db.add(row)
            await self.db.flush()

        fetched = await self.db.execute(
            select(AgentExperienceRow).where(AgentExperienceRow.id == str(exp.id))
        )
        updated_row = fetched.scalar_one()
        return _row_to_experience(updated_row)

    async def fetch_by_archetype(
        self, archetype: str, limit: int = 5
    ) -> list[AgentExperience]:
        result = await self.db.execute(
            select(AgentExperienceRow)
            .where(AgentExperienceRow.agent_archetype == archetype)
            .order_by(
                AgentExperienceRow.use_count.desc(),
                AgentExperienceRow.last_used_at.desc(),
            )
            .limit(limit)
        )
        rows = result.scalars().all()
        return [_row_to_experience(r) for r in rows]

    async def fetch_session_scoped(
        self, debate_id: str | UUID, archetype: str, limit: int = 5
    ) -> list[IntelligenceRecord]:
        """
        Fetches IntelligenceRecords scoped to a specific debate and filtered by
        agent_role matching the archetype. These are session-scoped observations
        as opposed to global AgentExperience entries.
        """
        result = await self.db.execute(
            select(IntelligenceRecordRow)
            .where(
                IntelligenceRecordRow.debate_id == str(debate_id),
                IntelligenceRecordRow.agent_role == archetype,
            )
            .order_by(IntelligenceRecordRow.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [_row_to_intelligence(r) for r in rows]

    async def bump_usage(self, experience_id: str | UUID) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(AgentExperienceRow)
            .where(AgentExperienceRow.id == str(experience_id))
            .values(
                use_count=AgentExperienceRow.use_count + 1,
                last_used_at=now,
            )
        )
        await self.db.flush()

    async def reset_all(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(AgentExperienceRow)
        )
        count = result.scalar_one()
        await self.db.execute(delete(AgentExperienceRow))
        await self.db.flush()
        return count
