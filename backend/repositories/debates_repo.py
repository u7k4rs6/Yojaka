from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import AgentAssignment, Debate, DebateStatus
from storage.models import DebateRow


def _row_to_debate(row: DebateRow) -> Debate:
    assignments_raw = json.loads(row.assignments_json) if row.assignments_json else []
    assignments = [AgentAssignment(**a) for a in assignments_raw]

    judge_config = json.loads(row.judge_config_json) if row.judge_config_json else {}
    analytics = json.loads(row.analytics_json) if row.analytics_json else None
    cost_summary = json.loads(row.cost_summary_json) if row.cost_summary_json else None
    practice_state = json.loads(row.practice_state_json) if row.practice_state_json else None
    phase_graph = json.loads(row.phase_graph_json) if row.phase_graph_json else None

    return Debate(
        id=UUID(row.id),
        session_id=UUID(row.session_id),
        topic=row.topic,
        pro_position=row.pro_position,
        con_position=row.con_position,
        status=DebateStatus(row.status),
        assignments=assignments,
        judge_config=judge_config,
        analytics=analytics,
        cost_summary=cost_summary,
        practice_state=practice_state,
        phase_graph=phase_graph,
        created_at=row.created_at,
    )


class DebatesRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        session_id: str | UUID,
        topic: str,
        mode: str,
        assignments: list[AgentAssignment],
    ) -> Debate:
        now = datetime.now(timezone.utc)
        row = DebateRow(
            id=str(uuid.uuid4()),
            session_id=str(session_id),
            topic=topic,
            pro_position=None,
            con_position=None,
            status=DebateStatus.PREPARING.value,
            assignments_json=json.dumps([a.model_dump(mode="json") for a in assignments]),
            judge_config_json=json.dumps({}),
            analytics_json=None,
            cost_summary_json=None,
            practice_state_json=None,
            phase_graph_json=None,
            created_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return _row_to_debate(row)

    async def get(self, debate_id: str | UUID) -> Optional[Debate]:
        result = await self.db.execute(
            select(DebateRow).where(DebateRow.id == str(debate_id))
        )
        row = result.scalar_one_or_none()
        return _row_to_debate(row) if row else None

    async def list_for_session(
        self, session_id: str | UUID, include_hidden: bool = False
    ) -> list[Debate]:
        # NOTE: There is no 'hidden' column in DebateRow; include_hidden is reserved
        # for future use. Currently all debates for the session are returned.
        stmt = (
            select(DebateRow)
            .where(DebateRow.session_id == str(session_id))
            .order_by(DebateRow.created_at.asc())
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_debate(r) for r in rows]

    async def update_status(self, debate_id: str | UUID, status: DebateStatus) -> None:
        await self.db.execute(
            update(DebateRow)
            .where(DebateRow.id == str(debate_id))
            .values(status=status.value if isinstance(status, DebateStatus) else status)
        )
        await self.db.flush()

    async def attach_analytics(
        self, debate_id: str | UUID, analytics_dict: dict
    ) -> None:
        await self.db.execute(
            update(DebateRow)
            .where(DebateRow.id == str(debate_id))
            .values(analytics_json=json.dumps(analytics_dict))
        )
        await self.db.flush()

    async def attach_cost_summary(
        self, debate_id: str | UUID, summary: dict
    ) -> None:
        await self.db.execute(
            update(DebateRow)
            .where(DebateRow.id == str(debate_id))
            .values(cost_summary_json=json.dumps(summary))
        )
        await self.db.flush()

    async def attach_phase_graph(
        self, debate_id: str | UUID, graph: dict
    ) -> None:
        await self.db.execute(
            update(DebateRow)
            .where(DebateRow.id == str(debate_id))
            .values(phase_graph_json=json.dumps(graph))
        )
        await self.db.flush()

    async def rename(self, debate_id: str | UUID, topic: str) -> Debate:
        await self.db.execute(
            update(DebateRow)
            .where(DebateRow.id == str(debate_id))
            .values(topic=topic)
        )
        await self.db.flush()
        debate = await self.get(debate_id)
        if debate is None:
            raise HTTPException(status_code=404, detail="Debate not found.")
        return debate

    async def hide(self, debate_id: str | UUID) -> None:
        # TODO: Add a `hidden` boolean column to DebateRow to implement soft-delete.
        # For now, perform a hard delete as a placeholder.
        await self.db.execute(
            delete(DebateRow).where(DebateRow.id == str(debate_id))
        )
        await self.db.flush()
